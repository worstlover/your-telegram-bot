#!/usr/bin/env python3
"""
Telegram Content Filter Bot
Main entry point for the bot application
"""

import threading
from flask import Flask

import logging
import os
import sys
from pathlib import Path # Import Path for directory creation
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

from config import Config
from bot_handlers import BotHandlers
from profanity_filter import ProfanityFilter
from media_manager import MediaManager
from user_manager import UserManager

# Web server to keep the bot alive on Render
app = Flask(__name__)
@app.route('/')
def index():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# +++ ADD THIS BLOCK TO ENSURE LOGS DIRECTORY EXISTS +++
LOGS_DIR = 'logs'
Path(LOGS_DIR).mkdir(exist_ok=True) # Create 'logs' directory if it doesn't exist
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'bot.log')), # Use os.path.join for path construction
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ... (بقیه کد run_bot و main_if_name_is_main بدون تغییر باقی می‌ماند)
# ...

def run_bot():
    """Main function to start the bot"""
    try:
        # ... (بقیه کد run_bot)
        
        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    run_bot()