import logging
import logging.config
import os
import asyncio
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from aiohttp import web
import pytz
from datetime import date, datetime
from aiohttp import web
from plugins import web_server
from info import SESSION, API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL, PORT
from pyrogram import types
from pyrogram import utils as pyroutils
from database.db import db

from apscheduler.schedulers.asyncio import AsyncIOScheduler

pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999

logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)


async def schedule_task_reset(self):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Kolkata"))
    scheduler.add_job(self.db.reset_daily_tasks, "cron", hour=0, minute=0, args=[self])  # Raat ke 12 baje reset hoga
    scheduler.start()




class Bot(Client):
    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=1000,
            plugins={"root": "plugins"},
            sleep_threshold=10,
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        logging.info(f"🤖 {me.first_name} (@{me.username}) running on Pyrogram v{__version__} (Layer {layer})")
        asyncio.create_task(schedule_task_reset(self))
        tz = pytz.timezone('Asia/Kolkata')
        today = date.today()
        now = datetime.now(tz)
        time = now.strftime("%H:%M:%S %p")
        await self.send_message(chat_id=LOG_CHANNEL, text=f"✅ Bot Restarted! 📅 Date: {today} 🕒 Time: {time}")
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()
        logging.info(f"🌐 Web Server Running on PORT {PORT}")

    async def stop(self, *args):
        await super().stop()
        logging.info("🛑 Bot Stopped.")

app = Bot()
app.run()
