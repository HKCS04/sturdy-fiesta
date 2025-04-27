from aiohttp import web
import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

# Telegram API credentials
BOT_TOKEN = "8087264479:AAEb7KMTxotET82ZW2xfXydCLpTj0uHsWLc"
APP_ID = "22136772"
API_HASH = "7541e5b6d298eb1f60dac89aae92868c"

PORT = "8080"
TG_BOT_WORKERS = "4"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            "primedlbot.txt",
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("AstroBotz")

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app




ascii_art = """

─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
─██████████████─██████████████─██████████████─████████████████───██████████████────██████████████───██████████████─██████████████─██████████████████─
─██░░░░░░░░░░██─██░░░░░░░░░░██─██░░░░░░░░░░██─██░░░░░░░░░░░░██───██░░░░░░░░░░██────██░░░░░░░░░░██───██░░░░░░░░░░██─██░░░░░░░░░░██─██░░░░░░░░░░░░░░██─
─██░░██████░░██─██░░██████████─██████░░██████─██░░████████░░██───██░░██████░░██────██░░██████░░██───██░░██████░░██─██████░░██████─████████████░░░░██─
─██░░██──██░░██─██░░██─────────────██░░██─────██░░██────██░░██───██░░██──██░░██────██░░██──██░░██───██░░██──██░░██─────██░░██─────────────████░░████─
─██░░██████░░██─██░░██████████─────██░░██─────██░░████████░░██───██░░██──██░░██────██░░██████░░████─██░░██──██░░██─────██░░██───────────████░░████───
─██░░░░░░░░░░██─██░░░░░░░░░░██─────██░░██─────██░░░░░░░░░░░░██───██░░██──██░░██────██░░░░░░░░░░░░██─██░░██──██░░██─────██░░██─────────████░░████─────
─██░░██████░░██─██████████░░██─────██░░██─────██░░██████░░████───██░░██──██░░██────██░░████████░░██─██░░██──██░░██─────██░░██───────████░░████───────
─██░░██──██░░██─────────██░░██─────██░░██─────██░░██──██░░██─────██░░██──██░░██────██░░██────██░░██─██░░██──██░░██─────██░░██─────████░░████─────────
─██░░██──██░░██─██████████░░██─────██░░██─────██░░██──██░░██████─██░░██████░░██────██░░████████░░██─██░░██████░░██─────██░░██─────██░░░░████████████─
─██░░██──██░░██─██░░░░░░░░░░██─────██░░██─────██░░██──██░░░░░░██─██░░░░░░░░░░██────██░░░░░░░░░░░░██─██░░░░░░░░░░██─────██░░██─────██░░░░░░░░░░░░░░██─
─██████──██████─██████████████─────██████─────██████──██████████─██████████████────████████████████─██████████████─────██████─────██████████████████─
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
"""

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={
                "root": "plugins"
            },
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER

    async def start(self):
        await super().start()
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()
        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info(f"Bot Running..!\n\nCreated by \nhttps://t.me/AstroBotz")
        print(ascii_art)
        print("""Welcome to CodeXBotz File Sharing Bot""")
        self.username = usr_bot_me.username
        #web-response
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")
