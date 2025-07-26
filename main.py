#!/usr/bin/env python3
"""
Telegram Content Filter Bot
Main entry point for the bot application
"""

# +++ ADD THESE IMPORTS AT THE TOP +++
import threading
from flask import Flask
# +++++++++++++++++++++++++++++++++++++

import logging
import os
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

from config import Config
from bot_handlers import BotHandlers
from profanity_filter import ProfanityFilter
from media_manager import MediaManager
from user_manager import UserManager

# +++ ADD THIS FLASK APP +++
# Web server to keep the bot alive on Render
app = Flask(__name__)
@app.route('/')
def index():
    return "Bot is alive!"

def run_flask():
    # Make sure to run on the port Render expects
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
# ++++++++++++++++++++++++++++

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log'),
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
            logger.error("Configuration validation failed. Please check your environment variables.")
            sys.exit(1) # Exit if essential configs are missing

        # Initialize managers
        # user_manager: Using default db_path "data/users.db"
        user_manager = UserManager() 
        profanity_filter = ProfanityFilter() # Assumes ProfanityFilter initializes with its default path
        media_manager = MediaManager() # Assumes MediaManager initializes with its default path

        # Initialize BotHandlers with all necessary managers and config
        handlers = BotHandlers(config, profanity_filter, media_manager, user_manager)

        application = Application.builder().token(config.BOT_TOKEN).build()

        # --- Register Handlers ---
        # Command handlers
        application.add_handler(CommandHandler("start", handlers.start_command))
        application.add_handler(CommandHandler("help", handlers.help_command))
        application.add_handler(CommandHandler("stats", handlers.stats_command))
        application.add_handler(CommandHandler("setname", handlers.set_name_command))
        
        # Admin commands
        application.add_handler(CommandHandler("adminstats", handlers.admin_stats_command, filters=filters.User(config.ADMIN_USER_ID) | filters.User(config.ADDITIONAL_ADMIN_IDS)))
        application.add_handler(CommandHandler("approveall", handlers.approve_all_command, filters=filters.User(config.ADMIN_USER_ID) | filters.User(config.ADDITIONAL_ADMIN_IDS)))
        application.add_handler(CommandHandler("rejectall", handlers.reject_all_command, filters=filters.User(config.ADMIN_USER_ID) | filters.User(config.ADDITIONAL_ADMIN_IDS)))
        application.add_handler(CommandHandler("clearqueue", handlers.clear_queue_command, filters=filters.User(config.ADMIN_USER_ID) | filters.User(config.ADDITIONAL_ADMIN_IDS)))
        
        # Message handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text_message))
        # Filters for different media types (if handled by handle_media_message)
        application.add_handler(MessageHandler(
            filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE | filters.DOCUMENT | filters.ANIMATION | filters.STICKER,
            handlers.handle_media_message
        ))
        
        # Callback query handler for inline keyboard buttons (e.g., admin approvals)
        application.add_handler(CallbackQueryHandler(handlers.handle_admin_callback))

        # Error handler
        async def error_callback(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            if isinstance(update, Update):
                await handlers.error_handler(update, context) # Assuming error_handler is in BotHandlers
            else:
                logger.error(f"An error occurred (no Update object): {context.error}")

        application.add_error_handler(error_callback)

        logger.info("Bot started successfully")
        logger.info(f"Channel ID: {config.CHANNEL_ID}")
        logger.info(f"Admin User ID: {config.ADMIN_USER_ID}")

        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES) # Use Update.ALL_TYPES for broader updates
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Run Flask in a separate thread to keep the bot alive on Render
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Run the bot in the main thread
    run_bot()