import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging

# Load environment variables
API_ID = int(os.getenv("API_ID", 22141398))  # Default value is provided
API_HASH = os.getenv("API_HASH", '0c8f8bd171e05e42d6f6e5a6f4305389')  # Default value is provided
BOT_TOKEN = os.getenv("BOT_TOKEN", '6346317908:AAH2nKFgF-MQOOzI_S30PZKNZK_aCoUhDC4')  # You should set the BOT_TOKEN as an environment variable

# Check if BOT_TOKEN is set
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set! Please set it as an environment variable.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Initialize the bot with your credentials from environment variables
bot = Client("terabox_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to fetch file details from the API
def get_file_details(link):
    try:
        api_url = f"https://tera-dl.vercel.app/api?link={link}"
        logger.info(f"Fetching file details for: {link}")
        
        response = requests.get(api_url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == "success":
                logger.info(f"File details fetched successfully for: {link}")
                return data['Extracted Info'][0]
        logger.error(f"Failed to fetch file details for: {link}. Status code: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error fetching file details for {link}: {e}")
        return None

# Function to download the file
def download_file(download_link, file_name, chat_id):
    try:
        logger.info(f"Downloading file: {file_name} from {download_link}")
        response = requests.get(download_link, stream=True)
        
        if response.status_code != 200:
            logger.error(f"Failed to download file from {download_link}. Status code: {response.status_code}")
            return None
        
        total_size = int(response.headers.get('Content-Length', 0))
        temp_file_path = f"downloads/{file_name}"
        
        if not os.path.exists("downloads"):
            os.makedirs("downloads")
        
        with open(temp_file_path, "wb") as f:
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded_size += len(chunk)
        
        logger.info(f"File downloaded successfully: {file_name}")
        return temp_file_path
    except Exception as e:
        logger.error(f"Error downloading the file: {e}")
        return None

# Handler for the '/Dl' command
@bot.on_message(filters.command("Dl"))
async def handle_download(client, message):
    link = message.text.split(" ")[1]  # Extract link from the command
    logger.info(f"Received TeraBox link from {message.from_user.username or message.from_user.id}: {link}")
    
    # Fetch file details
    file_details = get_file_details(link)

    if file_details:
        download_link = file_details.get("Direct Download Link")
        file_name = file_details.get("Title")
        
        caption = f"**File Name:** {file_name}\n**Download Link:** {download_link}"
        
        # Send a preview message to the user with file details
        await message.reply_text(f"✅ **Link is valid!** Here is the preview:\n\n{caption}")
        
        # Start the download
        file_path = download_file(download_link, file_name, message.chat.id)
        
        if file_path:
            try:
                logger.info(f"Sending file {file_name} to user")
                await message.reply_document(file_path, caption=f"**File Name:** {file_name}")
                os.remove(file_path)
                logger.info(f"File {file_name} sent successfully and deleted from local storage.")
            except Exception as e:
                logger.error(f"Error sending the file: {e}")
                await message.reply("Sorry, there was an error sending the file.")
        else:
            await message.reply("Sorry, there was an error downloading the file.")
    
    else:
        await message.reply("Sorry, I couldn't fetch the file details. Please check the link and try again.")

# Start the bot
bot.run()
