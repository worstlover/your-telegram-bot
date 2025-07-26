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
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

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
# ... (بقیه کد لاگین شما بدون تغییر باقی می‌ماند)
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
        # ... (تمام کد داخل تابع main شما اینجا قرار می‌گیرد)
        # Initialize configuration
        config = Config()

        # Validate required environment variables
        if not config.BOT_TOKEN:
            logger.error("BOT_TOKEN environment variable is required")
            sys.exit(1)

        if not config.CHANNEL_ID:
            logger.error("CHANNEL_ID environment variable is required")
            sys.exit(1)

        if not config.ADMIN_USER_ID:
            logger.error("ADMIN_USER_ID environment variable is required")
            sys.exit(1)

        # Initialize components
        profanity_filter = ProfanityFilter()
        media_manager = MediaManager()
        user_manager = UserManager()

        # Create application
        application = Application.builder().token(config.BOT_TOKEN).build()

        # Initialize handlers
        handlers = BotHandlers(config, profanity_filter, media_manager, user_manager)

        # ... (بقیه کد ثبت هندلرها بدون تغییر)
        application.add_handler(CommandHandler("start", handlers.start_command))
        application.add_handler(CommandHandler("help", handlers.help_command))
        application.add_handler(CommandHandler("pending", handlers.pending_command))
        application.add_handler(CommandHandler("stats", handlers.stats_command))
        application.add_handler(CallbackQueryHandler(handlers.button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text_message))
        application.add_handler(MessageHandler(filters.PHOTO, handlers.handle_media_message))
        application.add_handler(MessageHandler(filters.VIDEO, handlers.handle_media_message))
        # ... (الی آخر)

        from telegram.ext import ContextTypes as CT
        from telegram import Update
        async def error_callback(update: object, context: CT.DEFAULT_TYPE) -> None:
            if isinstance(update, Update):
                await handlers.error_handler(update, context)

        application.add_error_handler(error_callback)

        logger.info("Bot started successfully")
        logger.info(f"Channel ID: {config.CHANNEL_ID}")
        logger.info(f"Admin User ID: {config.ADMIN_USER_ID}")

        # Start the bot
        application.run_polling(allowed_updates=["message", "callback_query"])

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # main() # <--- این خط رو کامنت یا حذف کنید

    # +++ REPLACE with these lines to run both Flask and the Bot +++
    # Run Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Run the bot in the main thread
    run_bot()
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++