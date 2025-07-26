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
from pathlib import Path
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackQueryHandler, 
    ContextTypes
)

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

# Ensure logs directory exists
LOGS_DIR = 'logs'
Path(LOGS_DIR).mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'bot.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_bot():
    """Main function to start the bot"""
    try:
        # Initialize configuration
        config = Config()

        # Validate required configurations
        if not config.validate():
            logger.error("Configuration validation failed. Exiting.")
            sys.exit(1)

        # Initialize core components
        profanity_filter = ProfanityFilter()
        media_manager = MediaManager(config.PENDING_MEDIA_FILE)
        user_manager = UserManager(db_path="data/users.db") # Assuming users.db is in data folder

        # Initialize handlers
        handlers = BotHandlers(config, profanity_filter, media_manager, user_manager)

        # Build the Telegram Application
        application = Application.builder().token(config.BOT_TOKEN).build()

        # Register handlers
        # Commands
        application.add_handler(CommandHandler("start", handlers.start_command))
        application.add_handler(CommandHandler("help", handlers.help_command))
        application.add_handler(CommandHandler("set_name", handlers.set_name_command))
        application.add_handler(CommandHandler("my_name", handlers.my_name_command))
        application.add_handler(CommandHandler("admin_stats", handlers.admin_stats_command))
        application.add_handler(CommandHandler("add_profanity", handlers.add_profanity_command))
        
        # New: Command for showing main menu explicitly
        application.add_handler(CommandHandler("menu", handlers.show_main_menu)) 

        # Message Handlers for different types of content
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text_message))
        application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO | 
                                               filters.VOICE | filters.DOCUMENT | filters.ANIMATION | 
                                               filters.STICKER, handlers.handle_media_message))
        
        # Callback Query Handler for inline buttons (approval and menu interactions)
        application.add_handler(CallbackQueryHandler(handlers.button_callback))

        # Error handler
        async def error_callback(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            if isinstance(update, Update):
                await handlers.error_handler(update, context)

        application.add_error_handler(error_callback)

        logger.info("Bot started successfully")
        logger.info(f"Channel ID: {config.CHANNEL_ID}")
        logger.info(f"Admin User ID: {config.ADMIN_USER_ID}")

        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES) # Use ALL_TYPES to ensure all updates are caught

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Run Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Run the bot in the main thread
    run_bot()