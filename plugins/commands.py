import os
import asyncio
import re
import requests
from bot import Bot
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaDocument
import yt_dlp  # Using yt-dlp instead of youtube_dl
from PIL import Image  # for basic image validation

# Progress Bar Characters
BAR_FILLED = "█"
BAR_EMPTY = "░"
TOTAL_BAR_LENGTH = 20

# Telegram File Size Limit (4 GB)
MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024  # 4 GB in bytes

# Custom Thumbnail Path (Initialize to None)
CUSTOM_THUMBNAIL = {} #Dictionary for Multiple Users

# Custom Caption (Initialize to None)
CUSTOM_CAPTION = {} #Dictionary for Multiple Users


# Function to format progress bar
def format_progress_bar(percentage):
    """Formats a progress bar using decorative text symbols."""
    filled_length = int(TOTAL_BAR_LENGTH * percentage)
    bar = BAR_FILLED * filled_length + BAR_EMPTY * (TOTAL_BAR_LENGTH - filled_length)
    return bar

# Custom progress hook for yt-dlp (console output)
def progress_hook(d):
    """Displays download progress with a progress bar in the console."""
    if d['status'] == 'downloading':
        percentage = d['_percent_str']
        speed = d['_speed_str']
        eta = d['_eta_str']
        progress_bar = format_progress_bar(d['progress'] / 100)
        message = f"Downloading: {progress_bar} {percentage} | Speed: {speed} | ETA: {eta}"
        print(message)  # Log the progress in console

# Function to download and upload the video
async def download_and_upload(message: Message, url: str):
    """Downloads a video from a URL and uploads it to Telegram."""
    try:
        await message.reply_text("Downloading...")
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',  # Download best available video and audio
            'outtmpl': '%(title)s.%(ext)s',  # Output template
            'merge_output_format': 'mkv',  # Force mkv output to merge video and audio
            'progress_hooks': [progress_hook],  # Add the progress hook for console output
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)  # Download the url file
            file_path = ydl.prepare_filename(info_dict)  # Get the downloaded file path

        # Basic File Check
        if not os.path.exists(file_path):
            await message.reply_text("Error: File download failed.")
            return

        # Check File Size
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            await message.reply_text(f"Error: File size exceeds the maximum allowed size of 4 GB. File size: {file_size} bytes.")
            os.remove(file_path)  # Delete the downloaded file
            return

        # Sending to Telegram
        await message.reply_text("Uploading...")
        try:
            user_id = message.chat.id
            thumbnail = CUSTOM_THUMBNAIL.get(user_id)
            caption = CUSTOM_CAPTION.get(user_id, info_dict.get('title', 'Video from URL'))

            await app.send_document(chat_id=user_id, document=file_path,
                                  caption=caption, thumb=thumbnail,
                                  progress=upload_progress, progress_args=(user_id, "Uploading:"))

        except Exception as e:  # File limit reached
            await message.reply_text(f"Error: Uploading failed.\n{e}")  # File Limit reached or other error
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)  # Clean Up the downloaded file

        await message.reply_text("Download and Upload complete!")

    except yt_dlp.utils.DownloadError as e:
        await message.reply_text(f"Error: Download failed.\n{e}")

    except Exception as e:
        await message.reply_text(f"An unexpected error occurred:\n{e}")


# Custom upload progress function
async def upload_progress(current, total, chat_id, message_text):
    """Displays upload progress in Telegram chat action."""
    percentage = current / total
    progress_bar = format_progress_bar(percentage)
    message = f"{message_text} {progress_bar} {percentage * 100:.1f}%"
    try:
        await app.send_chat_action(chat_id, "upload_document")
    except Exception as e:
        print(f"Error during progress update : {e}")


# Command handler for setting custom thumbnail using user-sent image
@Bot.on_message(filters.photo)  # Listen for photo messages
async def setthumbnail_photo(client: Client, message: Message):
    """Sets the custom thumbnail to the photo sent by the user."""
    user_id = message.chat.id
    try:
        # Download the photo
        file_path = await client.download_media(message)  # Downloads the image
        try:
            # Validate it's an image (basic check)
            Image.open(file_path).verify()  # Raises exception if not an image or corrupted
            CUSTOM_THUMBNAIL[user_id] = file_path
            await message.reply_text("Custom thumbnail set successfully!")
        except Exception as e:
            await message.reply_text("Error: The file you sent is not a valid image.")
            os.remove(file_path) #removes file for the user
    except Exception as e:
        await message.reply_text(f"Error downloading image: {e}")
        if os.path.exists(file_path): #Removes the file
            os.remove(file_path)

# Command handler for setting custom caption
@Bot.on_message(filters.command("setcaption"))
async def setcaption_command(client: Client, message: Message):
    """Sets a custom caption for the user."""
    user_id = message.chat.id
    if len(message.command) > 1:
        caption = message.text.split(" ", 1)[1]
        CUSTOM_CAPTION[user_id] = caption
        await message.reply_text(f"Custom caption set to: {caption}")
    else:
        await message.reply_text("Usage: /setcaption <custom_caption>")

# Message handler for Prime Video links
@Bot.on_message(filters.regex(r"https:\/\/app\.primevideo\.com\/detail\?.*"))
async def primevideo_handler(client: Client, message: Message):
    """Handles messages containing Prime Video links."""
    url = message.text  # Get the URL from the message
    await download_and_upload(message, url)


# Command handler to start the bot
@Bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Start Command"""
    await message.reply_text(
        "Hello! Send me a Prime Video link, and I'll try to download and upload it for you. I will respond with the state of the download, upload and if it finished successfully. The progress is displayed on the console. Send a photo to set it as a custom thumbnail. You can also set custom captions for the video and a 4 GB File Restriction is applied."
    )
