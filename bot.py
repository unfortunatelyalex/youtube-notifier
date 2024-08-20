
import os
import sys
import json
import codecs
import logging
import sqlite3
import asyncio
import aiohttp
import nextcord
import traceback
from dotenv import load_dotenv
from nextcord.ext import commands
from logging.handlers import RotatingFileHandler


# Load environment variables
load_dotenv()

webhook_url = os.getenv('WEBHOOK_URL')

# Create a logger
logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)

# Clear any existing handlers to avoid duplicate logs
if logger.hasHandlers():
    logger.handlers.clear()

# Create a file handler with UTF-8 encoding
file_handler = RotatingFileHandler('bot.log', maxBytes=10000000, backupCount=3, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Create a console handler with UTF-8 encoding
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Create a formatter
formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s', datefmt='%d-%b-%Y %H:%M:%S')

# Set the formatter for both handlers
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Ensure the console output uses UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
else:
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

intents = nextcord.Intents.default()    
intents.message_content = True
bot = commands.Bot(intents=intents)

# Initialize SQLite database
def init_posted_videos():
    conn = sqlite3.connect('youtube_notifier.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posted_videos
                 (video_id TEXT PRIMARY KEY, channel_id TEXT, posted_at TIMESTAMP)''')
    conn.commit()
    conn.close()

# Initialize the channel_handles table if it doesn't exist
def init_handles():
    conn = sqlite3.connect('youtube_notifier.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS channel_handles
              (channel_id TEXT PRIMARY KEY, channel_handle TEXT)''')
    conn.commit()
    conn.close()

# Load configuration
def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            return json.load(f)
    return {'youtube_channels': [], 'notification_channel_id': None}

# Save configuration
def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

config = load_config()

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    init_posted_videos()
    init_handles()
    # Load cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')
                logger.info(f'Loaded {filename}')
            except Exception as e:
                logger.error(f"Error loading {filename}  -  TYPE {type(e).__name__}: {str(e)}")
                logger.error(traceback.format_exc())

    # Sync application commands
    try:
        await bot.sync_all_application_commands()
    except Exception as e:
        logger.error(f"Error syncing application commands  -  TYPE {type(e).__name__}: {e}")




async def send_webhook_message(message):
    if not isinstance(message, str):
        raise ValueError("The message must be a string.")
    payload = {"content": message, "username": "Error Notification Bot"}
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as response:
            if response.status == 204:
                logger.info("Successfully sent message to Discord webhook.")
            else:
                logger.error(f"Failed to send message to Discord webhook. Status code: {response.status}")



async def main():
    token = os.getenv('MUSIC_BOT_TOKEN')
    if not token:
        logger.error("No bot token found. Make sure MUSIC_BOT_TOKEN is set in your .env file.")
        return

    try:
        await bot.start(token)
    except Exception as e:
        logger.error(f"Error running the bot  -  TYPE {type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())