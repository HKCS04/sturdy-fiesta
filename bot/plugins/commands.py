import asyncio
import os
import re
import time
import traceback
from io import BytesIO
import logging

import aiohttp
import pyrogram
import requests
import yt_dlp
from PIL import Image
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.types import (CallbackQuery, InlineKeyboardButton,
                            InlineKeyboardMarkup, Message, InputMediaVideo)
from pyrogram.types import InputMediaPhoto
from pyrogram.types import Message as MSG
from yt_dlp import YoutubeDL

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

OWNER_ID = "8083702486"

MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024  # 4GB

# Initialize Pyrogram Client
app = Client(
    "TeraLinkUploaderBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# Global variables to store custom settings
CUSTOM_THUMBNAILS = {}
CUSTOM_CAPTIONS = {}

# YTDLP Configuration
YTDL_OPTS = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': '%(title)s-%(id)s.%(ext)s',  # Filename format
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'no_warnings': True,
    'source_address': '0.0.0.0',  # Bind to ipv4 since ipv6 addresses cause issues sometimes
    'progress_hooks': [],
}

# Progress bar symbols
BAR = [
    "▰",
    "▱",
]

def create_progress_bar(current, total):
    """Creates a fancy progress bar."""
    percentage = current / total
    filled_segments = int(percentage * 10)
    remaining_segments = 10 - filled_segments
    bar = BAR[0] * filled_segments + BAR[1] * remaining_segments
    return bar, percentage * 100

async def download_progress(current, total, message: MSG, start_time, file_name):
    """Displays download progress bar in Telegram."""
    now = time.time()
    diff = now - start_time
    if round(diff % 3) == 0:  # Update every 3 seconds
        bar, percentage = create_progress_bar(current, total)
        speed = current / diff
        eta = (total - current) / speed
        time_elapsed = time.strftime("%H:%M:%S", time.gmtime(diff))
        estimated_time = time.strftime("%H:%M:%S", time.gmtime(eta))

        try:
            await message.edit(
                text=f"**Downloading:** `{file_name}`\n"
                     f"**Progress:** `[{bar}] {percentage:.2f}%`\n"
                     f"**Speed:** `{speed / 1024:.2f} KB/s`\n"
                     f"**ETA:** `{estimated_time}`\n"
                     f"**Time Elapsed:** `{time_elapsed}`"
            )
        except MessageNotModified:
            pass
        except FloodWait as e:
            await asyncio.sleep(e.value)


async def upload_progress(current, total, message: MSG, start_time, file_name):
    """Displays upload progress bar in Telegram."""
    now = time.time()
    diff = now - start_time
    if round(diff % 3) == 0:  # Update every 3 seconds
        bar, percentage = create_progress_bar(current, total)
        speed = current / diff
        eta = (total - current) / speed
        time_elapsed = time.strftime("%H:%M:%S", time.gmtime(diff))
        estimated_time = time.strftime("%H:%M:%S", time.gmtime(eta))

        try:
            await message.edit(
                text=f"**Uploading:** `{file_name}`\n"
                     f"**Progress:** `[{bar}] {percentage:.2f}%`\n"
                     f"**Speed:** `{speed / 1024:.2f} KB/s`\n"
                     f"**ETA:** `{estimated_time}`\n"
                     f"**Time Elapsed:** `{time_elapsed}`"
            )
        except MessageNotModified:
            pass
        except FloodWait as e:
            await asyncio.sleep(e.value)


@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handles the /start command."""
    await message.reply_text(
        "Hi! I'm a TeraLink downloader and uploader bot.\n"
        "Send me a TeraFileshare or Terabox link and I'll download the file and upload it to Telegram.\n\n"
        "**Commands:**\n"
        "/start - Start the bot\n"
        "/set_thumbnail - Set a custom thumbnail\n"
        "/set_caption - Set a custom caption\n"
        "/reset_thumbnail - Reset to default thumbnail\n"
        "/reset_caption - Reset to default caption\n"
    )


@Client.on_message(filters.command("set_thumbnail"))
async def set_thumbnail(client: Client, message: Message):
    """Handles the /set_thumbnail command."""
    if message.reply_to_message and message.reply_to_message.photo:
        photo = await message.reply_to_message.download()
        CUSTOM_THUMBNAILS[message.from_user.id] = photo
        await message.reply_text("Custom thumbnail set!")
    else:
        await message.reply_text("Reply to a photo to set it as the thumbnail.")


@Client.on_message(filters.command("set_caption"))
async def set_caption(client: Client, message: Message):
    """Handles the /set_caption command."""
    caption = message.text.split(" ", 1)[1] if len(message.text.split(" ", 1)) > 1 else None
    if caption:
        CUSTOM_CAPTIONS[message.from_user.id] = caption
        await message.reply_text("Custom caption set!")
    else:
        await message.reply_text("Provide a caption after the command. Example: /set_caption My custom caption")


@Client.on_message(filters.command("reset_thumbnail"))
async def reset_thumbnail(client: Client, message: Message):
    """Handles the /reset_thumbnail command."""
    if message.from_user.id in CUSTOM_THUMBNAILS:
        del CUSTOM_THUMBNAILS[message.from_user.id]
        await message.reply_text("Custom thumbnail reset to default.")
    else:
        await message.reply_text("You don't have a custom thumbnail set.")


@Client.on_message(filters.command("reset_caption"))
async def reset_caption(client: Client, message: Message):
    """Handles the /reset_caption command."""
    if message.from_user.id in CUSTOM_CAPTIONS:
        del CUSTOM_CAPTIONS[message.from_user.id]
        await message.reply_text("Custom caption reset to default.")
    else:
        await message.reply_text("You don't have a custom caption set.")

def get_terabox_direct_link(terabox_url):
    """Extracts the direct download link from a Terabox URL."""
    try:
        url = f"https://terabox-dl.herokuapp.com/getLink?url={terabox_url}"
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        direct_link = data.get("direct_link")
        return direct_link
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during request: {e}")
        return None
    except (ValueError, KeyError) as e:
        logging.error(f"Error parsing JSON: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

def get_terafileshare_direct_link(terafileshare_url):
    """Extracts the direct download link from a TeraFileshare URL."""
    try:
        response = requests.get(terafileshare_url)
        response.raise_for_status()
        # Check if request was successful

        # Extract download link using regex.  More robust regex.
        download_link_match = re.search(r'href="(https?://[^"]*?download[^"]*)"', response.text)
        if download_link_match:
            direct_link = download_link_match.group(1)
            return direct_link
        else:
            logging.warning("No direct download link found in the HTML.")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Error during request: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

async def download_and_upload(client: Client, message: Message, link: str):
    """Downloads a file and uploads it to Telegram, handling both Terabox and TeraFileshare links."""
    user_id = message.from_user.id
    direct_link = None

    # Determine the link type and extract the direct link
    if "terabox.com" in link:
        logging.info("Detected Terabox link.")
        direct_link = get_terabox_direct_link(link)
    elif "terafileshare.com" in link:
        logging.info("Detected TeraFileshare link.")
        direct_link = get_terafileshare_direct_link(link)
    else:
        await message.reply_text("Unsupported link type.  Only Terabox and TeraFileshare links are supported.")
        return

    if not direct_link:
        await message.reply_text("Failed to extract the direct download link.")
        return

    try:
        file_name = direct_link.split("/")[-1]  # Simplified file name extraction
    except:
        file_name = "FileFromLink"


    # Check file size before downloading
    async with aiohttp.ClientSession() as session:
        try:
            async with session.head(direct_link, allow_redirects=True) as resp: # allow_redirects=True important
                file_size = int(resp.headers.get('Content-Length', 0))
                if file_size > MAX_FILE_SIZE:
                    await message.reply_text(f"File size exceeds the maximum allowed size of 4GB. File size: {file_size / (1024 * 1024 * 1024):.2f} GB")
                    return
        except Exception as e:
            await message.reply_text(f"Failed to check file size. Error: {str(e)}")
            logging.error(f"File size check error: {e}")
            return


    start_time = time.time()
    download_message = await message.reply_text(f"Starting download of `{file_name}`...")
    temp_file_path = f"./downloads/{file_name}"  # Save to a directory
    os.makedirs("./downloads", exist_ok=True)  # Ensure the directory exists

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(direct_link, allow_redirects=True) as response: # allow_redirects=True here too!
                if response.status == 200:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded_size = 0
                    with open(temp_file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024): # 1MB chunks
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            await download_progress(downloaded_size, total_size, download_message, start_time, file_name)
                else:
                    await message.reply_text(f"Download failed with status code: {response.status}")
                    return

        await download_message.edit_text(f"Download complete! Starting upload...")

        # Upload to Telegram
        start_time = time.time()
        upload_message = await message.reply_text(f"Starting upload of `{file_name}`...")


        try:
            thumb = CUSTOM_THUMBNAILS.get(user_id)

            # If user has no custom thumbnail set, try to automatically extract a thumbnail
            if not thumb:
                 try:
                     # Attempt to extract thumbnail using yt-dlp
                     ydl_opts = {'writesubtitles': False, 'writethumbnail': True, 'quiet': True, 'no_warnings': True}
                     with YoutubeDL(ydl_opts) as ydl:
                         info_dict = ydl.extract_info(temp_file_path, download=False)
                         if 'thumbnail' in info_dict:
                             thumb = info_dict['thumbnail']
                             # Download the thumbnail if it's a URL
                             if thumb.startswith('http'):
                                 async with aiohttp.ClientSession() as session:
                                     async with session.get(thumb) as resp:
                                         if resp.status == 200:
                                             thumb = BytesIO(await resp.read()) # Store thumbnail data in memory
                                             print("Successfully downloaded thumbnail from URL.")
                                         else:
                                             print(f"Failed to download thumbnail from URL: {resp.status}")
                                             thumb = None
                         else:
                            print("No thumbnail found using yt-dlp.")
                            thumb = None

                 except Exception as e:
                    print(f"Error extracting thumbnail: {e}")
                    thumb = None


            # Default caption
            caption = CUSTOM_CAPTIONS.get(user_id, f"Uploaded by @{Client.me.username}")

            # Get video duration for proper display in Telegram.  This is important
            duration = 0 # Set Default
            try:
                ydl_opts = {'quiet': True, 'no_warnings': True}
                with YoutubeDL(ydl_opts) as ydl:
                   info_dict = ydl.extract_info(temp_file_path, download=False)
                   duration = info_dict.get('duration', 0)
            except Exception as e:
                print(f"Failed to get video duration: {e}")


            await Client.send_video(
                chat_id=message.chat.id,
                video=temp_file_path,
                caption=caption,
                supports_streaming=True,
                thumb=thumb,
                duration=duration, # Pass duration
                progress=upload_progress,
                progress_args=(upload_message, start_time, file_name)
            )

            await upload_message.delete()
            await message.reply_text("Upload complete!")

        except Exception as e:
            await message.reply_text(f"Upload failed: {e}\n\n{traceback.format_exc()}") # Provide full traceback
            logging.error(f"Upload error: {e}\n{traceback.format_exc()}")

    finally:
        try:
            os.remove(temp_file_path) # Clean up the downloaded file
        except Exception as e:
            print(f"Failed to delete temporary file: {e}")


@Client.on_message(filters.regex(r"https?://(?:www\.)?(terabox\.com|terafileshare\.com)/\S+"))
async def link_handler(client: Client, message: Message):
    """Handles messages containing Terabox and TeraFileshare links."""
    link = message.text.strip()
    await download_and_upload(client, message, link)
