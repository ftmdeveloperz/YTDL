import os
import requests
from pyrogram import Client, filters
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
        # Replace this URL with your API
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
def download_file(download_link, file_name):
    try:
        logger.info(f"Downloading file: {file_name} from {download_link}")
        response = requests.get(download_link, stream=True)
        
        # Check if the response is valid
        if response.status_code != 200:
            logger.error(f"Failed to download file from {download_link}. Status code: {response.status_code}")
            return None
        
        temp_file_path = f"downloads/{file_name}"
        
        # Make sure the downloads directory exists
        if not os.path.exists("downloads"):
            os.makedirs("downloads")
        
        with open(temp_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"File downloaded successfully: {file_name}")
        return temp_file_path
    except Exception as e:
        logger.error(f"Error downloading the file: {e}")
        return None

# Handler to process incoming messages
@bot.on_message(filters.regex(r"^(https?://)"))
async def handle_message(client, message):
    link = message.text.strip()
    logger.info(f"Received TeraBox link from {message.from_user.username or message.from_user.id}: {link}")
    
    # Fetch file details from your API
    file_details = get_file_details(link)

    if file_details:
        # Get the direct download link and other details
        download_link = file_details.get("Direct Download Link")
        file_name = file_details.get("Title")
        size = file_details.get("Size")
        thumbnail = file_details['Thumbnails'].get("850x580")
        
        # Prepare the caption
        caption = f"**File Name:** {file_name}\n**Size:** {size}\n[Download Now]({download_link})"
        logger.info(f"Caption: {caption}")
        
        # Send a preview message to the user with file details (thumbnails, title, etc.)
        await message.reply_text(
            f"✅ **Link is valid!** Here is the preview:\n\n"
            f"**Title:** {file_name}\n"
            f"**Size:** {size}\n"
            f"[Download Link]({download_link})\n\n"
            f"Here is the thumbnail preview for the file:",
            reply_markup=None
        )
        
        if thumbnail:
            await message.reply_photo(thumbnail, caption=f"**File Preview**\n{caption}")
        else:
            await message.reply_text("No thumbnail available for this file.")

        # Now ask user for confirmation to proceed with download
        await message.reply_text(
            "Do you want to proceed with the download? (Reply 'Yes' to proceed or 'No' to cancel)"
        )
        
        # Store user's choice
        user_choice = None

        # Wait for user response (the bot listens for the next message)
        @bot.on_message(filters.text & filters.user(message.from_user.id))
        async def user_reply(client, msg):
            nonlocal user_choice
            user_choice = msg.text.strip().lower()
            
            if user_choice == "yes":
                # Proceed with download
                file_path = download_file(download_link, file_name)
                
                if file_path:
                    # Send the file directly to the user
                    try:
                        logger.info(f"Sending file {file_name} to user: {message.from_user.username or message.from_user.id}")
                        if thumbnail:
                            await message.reply_document(file_path, caption=caption, thumb=thumbnail)
                        else:
                            await message.reply_document(file_path, caption=caption)
                        
                        os.remove(file_path)  # Clean up the downloaded file after sending
                        logger.info(f"File {file_name} sent successfully and deleted from local storage.")
                    except Exception as e:
                        logger.error(f"Error sending the file to the user: {e}")
                        await message.reply("Sorry, there was an error sending the file.")
                else:
                    logger.error(f"Failed to download file: {file_name}")
                    await message.reply("Sorry, there was an error downloading the file.")
            elif user_choice == "no":
                await message.reply("Download canceled.")
            else:
                await message.reply("Invalid response. Please reply with 'Yes' or 'No'.")
    
    else:
        # If there was an error or no data, inform the user
        logger.error(f"Failed to fetch file details for link: {link}")
        await message.reply("Sorry, I couldn't fetch the file details. Please check the link and try again.")

# Start the bot
bot.run()
