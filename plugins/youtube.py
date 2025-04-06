import os
import logging
import yt_dlp
import aiohttp
import aiofiles
import asyncio
import time
import math
import random
import string
import psutil
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from threading import Thread
from database.db import db
from PIL import Image

active_tasks = {}

def humanbytes(size):
    if not size:
        return "N/A"
    power = 2**10
    n = 0
    units = ["", "K", "M", "G", "T"]
    while size > power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{round(size, 2)}{units[n]}B"

def TimeFormatter(milliseconds):
    seconds = milliseconds // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start

    if current == total or round(diff % 5.00) == 0:
        percentage = (current / total) * 100
        speed = current / diff if diff > 0 else 0
        estimated_total_time = TimeFormatter(milliseconds=(total - current) / speed * 1000) if speed > 0 else "∞"

        # CPU & RAM Usage
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent

        # Progress Bar
        progress_bar = "■" + "■" * math.floor(percentage / 5) + "□" * (20 - math.floor(percentage / 5))

        text = (
            f"**╭───────Uᴘʟᴏᴀᴅɪɴɢ───────〄**\n"
            f"**│**\n"
            f"**├📁 Sɪᴢᴇ : {humanbytes(current)} ✗ {humanbytes(total)}**\n"
            f"**│**\n"
            f"**├📦 Pʀᴏɢʀᴇꜱꜱ : {round(percentage, 2)}%**\n"
            f"**│**\n"
            f"**├🚀 Sᴘᴇᴇᴅ : {humanbytes(speed)}/s**\n"
            f"**│**\n"
            f"**├⏱️ Eᴛᴀ : {estimated_total_time}**\n"
            f"**│**\n"
            f"**├🏮 Cᴘᴜ : {cpu_usage}%  |  Rᴀᴍ : {ram_usage}%**\n"
            f"**│**\n"
            f"**╰─[{progress_bar}]**"
        )

        try:
            await message.edit(text=text)
        except:
            pass

async def progress_bar(current, total, status_message, start_time, last_update_time):
    """Display a progress bar for downloads/uploads."""
    elapsed_time = time.time() - start_time
    percentage = (current / total) * 100
    speed = current / elapsed_time / 1024 / 1024  # Speed in MB/s
    uploaded = current / 1024 / 1024  # Uploaded size in MB
    total_size = total / 1024 / 1024  # Total size in MB
    remaining_size = total_size - uploaded  # Remaining MB
    eta = (remaining_size / speed) if speed > 0 else 0  # Estimated time in seconds

    # Convert ETA to minutes & seconds
    eta_min = int(eta // 60)
    eta_sec = int(eta % 60)

    # Get system usage stats
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent

    # Generate progress bar
    progress_blocks = int(percentage // 5)
    progress_bar = "■" + "■" * progress_blocks + "□" * (20 - progress_blocks)

    # Throttle updates: Only update if at least 2 seconds have passed
    if time.time() - last_update_time[0] < 2:
        return
    last_update_time[0] = time.time()

    text = (
        "**╭───────Dᴏᴡɴʟᴏᴀᴅɪɴɢ───────〄**\n"
        "**│**\n"
        f"**├📁 Sɪᴢᴇ : {uploaded:.2f} 𝙼𝙱 ✗ {total_size:.2f} 𝙼𝙱**\n"
        "**│**\n"
        f"**├📦 Pʀᴏɢʀᴇꜱꜱ : {percentage:.2f}%**\n"
        "**│**\n"
        f"**├🚀 Sᴘᴇᴇᴅ : {speed:.2f} 𝙼𝙱/s**\n"
        "**│**\n"
        f"**├⏱️ Eᴛᴀ : {eta_min}𝚖𝚒𝚗, {eta_sec}𝚜𝚎𝚌**\n"
        "**│**\n"
        f"**├🏮 Cᴘᴜ : {cpu_usage}%  |  Rᴀᴍ : {ram_usage}%**\n"
        "**│**\n"
        f"**╰─[{progress_bar}]**"
    )

    try:
        await status_message.edit(text)
    except Exception as e:
        print(f"Error updating progress: {e}")

async def update_progress(message, queue):
    """Updates progress bar while downloading."""
    last_update_time = [0]  # Use a list to store the last update time as a mutable object
    start_time = time.time()

    while True:
        data = await queue.get()
        if data is None:
            break

        current, total, status = data
        await progress_bar(current, total, message, start_time, last_update_time)

def yt_progress_hook(d, queue, client):
    """Reports progress of yt-dlp to async queue in a thread-safe way."""
    if d['status'] == 'downloading':
        current = d['downloaded_bytes']
        total = d.get('total_bytes', 1)
        asyncio.run_coroutine_threadsafe(queue.put((current, total, "⬇ **Downloading...**")), client.loop)
    elif d['status'] == 'finished':
        asyncio.run_coroutine_threadsafe(queue.put((1, 1, "✅ **Download Complete! Uploading...**")), client.loop)
        asyncio.run_coroutine_threadsafe(queue.put(None), client.loop)  # Stop progress loop

async def download_and_resize_thumbnail(url, save_path="thumbnail.jpg"):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

            img = Image.open(save_path).convert("RGB")
            img.save(save_path, "JPEG", quality=85)

            return save_path
    except Exception as e:
        logging.exception("Thumbnail download failed: %s", e)
    return None

async def upload_video(client, chat_id, output_filename, caption, duration, width, height, thumbnail_path, status_msg):
    if output_filename and os.path.exists(output_filename):
        await status_msg.edit_text("📤 **Uploading video...**")
        start_time = time.time()

        async def upload_progress(sent, total):
            await progress_for_pyrogram(sent, total, "📤 **Uploading...**", status_msg, start_time)

        try:
            with open(output_filename, "rb") as video_file:
                await client.send_video(
                    chat_id=chat_id,
                    video=video_file,  # File streaming enabled
                    progress=upload_progress,
                    caption=caption,
                    duration=duration,
                    supports_streaming=True,
                    height=height,
                    width=width,
                    disable_notification=True,
                    thumb=thumbnail_path if thumbnail_path else None,
                    file_name=os.path.basename(output_filename)
                )

            await status_msg.edit_text("✅ **Upload Successful!**")
            await db.increment_task(chat_id)            
            await status_msg.delete()

        except Exception as e:
            await status_msg.edit_text(f"❌ **Upload Failed!**\nError: {e}")

        finally:
            if os.path.exists(output_filename):
                os.remove(output_filename)
            if thumbnail_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            active_tasks.pop(chat_id, None)

           
    else:
        await status_msg.edit_text("❌ **Upload Failed!**")
        active_tasks.pop(chat_id, None)
        

async def download_video(client, callback_query, chat_id, youtube_link, format_id):
    if active_tasks.get(chat_id):
        await client.send_message(chat_id, "⏳ **Your previous task is still running. Please wait!**")
        return

    active_tasks[chat_id] = True  # Mark task as active
    status_msg = await client.send_message(chat_id, "⏳ **Starting Download...**")
    await callback_query.message.delete()
    
    queue = asyncio.Queue()
    output_filename = None
    caption = ""
    duration = 0
    width, height = 360, 360
    thumbnail_path = None
    youtube_thumbnail_url, thumbnails = None, []
    
    timestamp = time.strftime("%y%m%d")
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=3))

    def run_yt_dlp():
        nonlocal output_filename, caption, duration, width, height, youtube_thumbnail_url, thumbnails
        yt_dlp_options = {
            'format': f"{format_id}+bestaudio/best",
            'merge_output_format': 'mp4',
            'outtmpl': f"downloads/%(title)s_{timestamp}-{random_str}.%(ext)s",
            'progress_hooks': [lambda d: yt_progress_hook(d, queue, client)],
            'cookiefile': 'cookies.txt'
        }

        with yt_dlp.YoutubeDL(yt_dlp_options) as ydl:
            info = ydl.extract_info(youtube_link, download=True)
            caption = info.get('title', '')
            duration = info.get('duration', 0)
            width, height = info.get('width', 360), info.get('height', 360)
            youtube_thumbnail_url = info.get('thumbnail', '')
            thumbnails = info.get('thumbnails', [])
            
            if 'requested_downloads' in info and info['requested_downloads']:
                output_filename = info['requested_downloads'][-1]['filepath']
            else:
                output_filename = info.get('filepath', None)

    thread = Thread(target=run_yt_dlp)
    thread.start()
    
    await update_progress(status_msg, queue)
    thread.join()

    if output_filename and os.path.exists(output_filename):
        await status_msg.edit_text("📤 **Preparing for upload...**")
        thumbnail_file_id = await db.get_user_thumbnail(chat_id)
        if thumbnail_file_id:
            try:
                thumb_message = await client.download_media(thumbnail_file_id)
                thumbnail_path = thumb_message
            except Exception as e:
                print(f"Thumbnail download error: {e}")

        if not thumbnail_path and thumbnails:
            high_quality_thumb = max(thumbnails, key=lambda x: x.get('height', 0))['url']
            if high_quality_thumb:
                thumbnail_path = await download_and_resize_thumbnail(high_quality_thumb)

        await upload_video(client, chat_id, output_filename, caption, duration, width, height, thumbnail_path, status_msg)
    else:
        await status_msg.edit_text("❌ **Download Failed!**")
        active_tasks.pop(chat_id, None)
   

@Client.on_message(filters.regex(r'^(http(s)?:\/\/)?((w){3}.)?youtu(be|.be)?(\.com)?\/.+'))
async def process_youtube_link(client, message):
    chat_id = message.chat.id

    fetching_message = await message.reply_text("🔍 **Fetching available formats... Please wait a moment!**")
    
    if not await db.check_task_limit(chat_id):
        await message.reply_text("❌ **You have reached your daily task limit! Try again tomorrow.**")
        await fetching_message.delete()
        return
        
    if active_tasks.get(chat_id):
        await message.reply_text("⏳ **Your previous task is still running. Please wait!**")
        await fetching_message.delete()
        return

    youtube_link = message.text
    keyboard_buttons = []

   
    try:
        loop = asyncio.get_event_loop()
        info_dict = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL({'quiet': True, 'cookiefile': 'cookies.txt'}).extract_info(youtube_link, download=False))
        formats = info_dict.get('formats', [])
        title = info_dict.get('title', 'No title available')
        thumbnail_url = info_dict.get('thumbnail', '')

        quality_options = {}
        for f in formats:
            height = f.get('height')
            format_id = f.get('format_id')
            filesize = f.get('filesize') or f.get('filesize_approx')
            if height and format_id and height >= 144:
                if filesize:
                    quality_options[str(height)] = (format_id, filesize)

        sorted_qualities = sorted(quality_options.keys(), key=lambda x: int(x), reverse=True)
        for quality in sorted_qualities:
            format_id, filesize = quality_options[quality]
            size_text = f"{round(filesize / 1024 / 1024, 1)}MB"
            keyboard_buttons.append([InlineKeyboardButton(f"🎬 {quality}p - {size_text}", callback_data=f"download|{format_id}")])

    except Exception as e:
        logging.exception("Error fetching available formats: %s", e)
        await message.reply_text("⚠️ **Oops! Something went wrong while fetching the formats. Please try again later.**")
        return
    
    if keyboard_buttons:
        if thumbnail_url:
            sent_msg = await message.reply_photo(
                thumbnail_url,
                caption=f"**🎥 Title:** {title}\n\n**✨ Choose Video Quality to Download:**",
                reply_markup=InlineKeyboardMarkup(keyboard_buttons),
                reply_to_message_id=message.id
            )
            await fetching_message.delete()
    else:
        await message.reply_text("❌ **Sorry! No available video formats found for this link.**")
        


@Client.on_callback_query(filters.regex(r'^download\|'))
async def handle_download_button(client, callback_query):
    format_id = callback_query.data.split('|')[1]
    youtube_link = callback_query.message.reply_to_message.text
    chat_id = callback_query.message.chat.id
    await download_video(client, callback_query, chat_id, youtube_link, format_id)
