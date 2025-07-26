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
    filters,  # Import filters directly
    CallbackQueryHandler,
    ContextTypes
)
# Removed explicit imports like: from telegram.ext.filters import Photo, Video, Audio, Voice, Document, Animation, Sticker


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
        config = Config()
        if not config.validate():
            sys.exit(1)

        profanity_filter = ProfanityFilter(config.PROFANITY_WORDS_FILE)
        media_manager = MediaManager(config.PENDING_MEDIA_FILE)
        user_manager = UserManager() # Initialize UserManager

        handlers = BotHandlers(config, profanity_filter, media_manager, user_manager)

        application = Application.builder().token(config.BOT_TOKEN).build()

        # Command Handlers
        application.add_handler(CommandHandler("start", handlers.start_command))
        application.add_handler(CommandHandler("help", handlers.help_command))
        # تغییر در این خط: 'stats_command' به 'admin_stats_command' تغییر یافت.
        application.add_handler(CommandHandler("stats", handlers.admin_stats_command))
        application.add_handler(CommandHandler("set_name", handlers.set_name_command))
        # اضافه شدن این خط: برای فعال کردن دستور /my_name
        application.add_handler(CommandHandler("my_name", handlers.my_name_command))
        application.add_handler(CommandHandler("cancel", handlers.cancel_command))
        application.add_handler(CommandHandler("admin_menu", handlers.admin_menu_command))
        application.add_handler(CommandHandler("ban", handlers.ban_user_command)) # New ban command handler
        application.add_handler(CommandHandler("unban", handlers.unban_user_command)) # New unban command handler
        application.add_handler(CommandHandler("check_ban", handlers.check_ban_command)) # New check ban command handler
        application.add_handler(CommandHandler("add_profanity", handlers.add_profanity_command)) # Add handler for /add_profanity
        application.add_handler(CommandHandler("remove_profanity", handlers.remove_profanity_command)) # Add handler for /remove_profanity
        application.add_handler(CommandHandler("list_profanity", handlers.list_profanity_command)) # Add handler for /list_profanity
        application.add_handler(CommandHandler("set_strict_filtering", handlers.set_strict_filtering_command)) # Add handler for /set_strict_filtering


        # Menu Handler - useful for showing main menu explicitly
        application.add_handler(CommandHandler("menu", handlers.show_main_menu))

        # Message Handlers for different types of content
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text_message))
        # Corrected: Use filters.ATTACHMENT to cover all media types
        application.add_handler(MessageHandler(filters.ATTACHMENT, handlers.handle_media_message))

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