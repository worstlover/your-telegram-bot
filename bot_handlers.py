"""
Telegram bot handlers for processing messages and commands
"""

import logging
import time
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import html # Import html for escaping
import json # Import json for dumps

from config import Config
from profanity_filter import ProfanityFilter
from media_manager import MediaManager, PendingMedia
from user_manager import UserManager, UserProfile # Ensure UserProfile is imported if used

logger = logging.getLogger(__name__)

class BotHandlers:
    """Handler class for all bot interactions"""

    def __init__(self, config: Config, profanity_filter: ProfanityFilter, media_manager: MediaManager, user_manager: UserManager):
        self.config = config
        self.profanity_filter = profanity_filter
        self.media_manager = media_manager
        self.user_manager = user_manager
        self.stats = {
            "messages_processed": 0,
            "messages_filtered": 0,
            "messages_posted": 0,
            "media_pending": 0,
            "media_approved": 0,
            "media_rejected": 0
        }

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        if not user:
            return

        # Register or get user profile
        user_profile = self.user_manager.register_user(user.id, user.username or user.first_name or "Unknown")

        # Increment message count for the user
        self.user_manager.increment_message_count(user.id)
        self.stats["messages_processed"] += 1

        # Check if user is banned
        if self.user_manager.is_user_banned(user.id):
            await update.message.reply_text("شما از استفاده از ربات منع شده‌اید.")
            logger.warning(f"Banned user {user.id} tried to use /start command.")
            return

        welcome_message = (
            f"سلام {user_profile.display_name} عزیز! 👋\n"
            "به ربات فیلتر محتوای تلگرام خوش آمدید.\n"
            "من اینجا هستم تا به شما کمک کنم محتوای خود را قبل از ارسال به کانال فیلتر کنید."
        )
        await update.message.reply_text(welcome_message)
        await self.show_main_menu(update, context)


    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if self.user_manager.is_user_banned(user_id):
            await update.message.reply_text("شما از استفاده از ربات منع شده‌اید.")
            logger.warning(f"Banned user {user_id} tried to use /help command.")
            return

        help_text = (
            "لیست دستورات:\n"
            "/start - شروع کار با ربات\n"
            "/help - نمایش این راهنما\n"
            "/set_name - تنظیم نام نمایشی شما\n"
            "/my_name - نمایش نام نمایشی فعلی شما\n"
            "/stats - نمایش آمار استفاده (فقط برای ادمین)\n"
            "/menu - نمایش منوی اصلی\n"
            "/cancel - لغو عملیات فعلی\n"
            "\n"
            "فقط کافیست متن، عکس، ویدئو یا هر نوع رسانه‌ای را برای من بفرستید تا بررسی کنم."
        )
        if self.config.is_admin(user_id):
            help_text += (
                "\n\n**دستورات ادمین:**\n"
                "/admin_menu - دسترسی به منوی ادمین\n"
                "/ban [user_id] - بن کردن کاربر\n"
                "/unban [user_id] - خارج کردن کاربر از بن\n"
                "/check_ban [user_id] - بررسی وضعیت بن کاربر\n"
                "/add_profanity [lang] [word] - افزودن کلمه توهین‌آمیز (مثال: `/add_profanity fa کلمه`)\n"
                "/remove_profanity [lang] [word] - حذف کلمه توهین‌آمیز (مثال: `/remove_profanity fa کلمه`)\n"
                "/list_profanity [lang] - لیست کلمات توهین‌آمیز (مثال: `/list_profanity fa`)\n"
                "/set_strict_filtering [true/false] - تنظیم فیلترینگ سختگیرانه (مثال: `/set_strict_filtering true`)\n"
            )
        await update.message.reply_text(help_text)

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu with inline buttons"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if self.user_manager.is_user_banned(user_id):
            await update.message.reply_text("شما از استفاده از ربات منع شده‌اید.")
            logger.warning(f"Banned user {user_id} tried to access main menu.")
            return

        keyboard = [
            [InlineKeyboardButton("📝 تغییر نام نمایشی", callback_data="set_name")],
            [InlineKeyboardButton("📊 آمار ربات (ادمین)", callback_data="admin_stats")] # Changed to admin_stats
        ]
        if self.config.is_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ منوی ادمین", callback_data="admin_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text("لطفاً یک گزینه را انتخاب کنید:", reply_markup=reply_markup)

    async def set_name_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set_name command to allow user to set display name"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if self.user_manager.is_user_banned(user_id):
            await update.message.reply_text("شما از استفاده از ربات منع شده‌اید.")
            logger.warning(f"Banned user {user_id} tried to use /set_name command.")
            return

        self.user_manager.set_user_setting_name_mode(user_id, True)
        await update.message.reply_text("لطفاً نام نمایشی جدید خود را ارسال کنید:")

    async def _set_user_display_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_name: str):
        """Internal method to handle setting user display name"""
        user_id = update.effective_user.id
        if not new_name or len(new_name) < 3 or len(new_name) > 20:
            await update.message.reply_text("نام نمایشی باید بین 3 تا 20 کاراکتر باشد.")
            self.user_manager.set_user_setting_name_mode(user_id, False)
            return

        if self.user_manager.set_display_name(user_id, new_name):
            user_profile = self.user_manager.get_user_profile(user_id) # Fetch updated profile
            await update.message.reply_text(f"نام نمایشی شما با موفقیت به '{user_profile.display_name}' تغییر یافت.")
            logger.info(f"User {user_id} changed display name to '{new_name}'")
        else:
            await update.message.reply_text("این نام نمایشی قبلاً استفاده شده است. لطفاً نام دیگری را انتخاب کنید.")
            logger.warning(f"User {user_id} failed to set display name to '{new_name}' (name taken)")
        self.user_manager.set_user_setting_name_mode(user_id, False)


    async def my_name_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /my_name command to display current display name"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if self.user_manager.is_user_banned(user_id):
            await update.message.reply_text("شما از استفاده از ربات منع شده‌اید.")
            logger.warning(f"Banned user {user_id} tried to use /my_name command.")
            return

        user_profile = self.user_manager.get_user_profile(user_id)
        if user_profile:
            await update.message.reply_text(f"نام نمایشی فعلی شما: '{user_profile.display_name}'")
        else:
            await update.message.reply_text("اطلاعات کاربری شما یافت نشد.")

    async def admin_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin_stats command to show bot statistics (admin only)"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if not self.config.is_admin(user_id):
            await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
            logger.warning(f"Non-admin user {user_id} tried to use /admin_stats command.")
            return

        user_stats = self.user_manager.get_user_stats()
        media_stats = self.media_manager.get_media_stats()

        stats_message = (
            "📊 **آمار ربات** 📊\n\n"
            "**آمار پیام‌ها:**\n"
            f"  تعداد کل پیام‌های پردازش شده: {self.stats['messages_processed']}\n"
            f"  تعداد پیام‌های فیلتر شده: {self.stats['messages_filtered']}\n"
            f"  تعداد پیام‌های ارسال شده به کانال: {self.stats['messages_posted']}\n"
            "\n"
            "**آمار رسانه‌ها (درحال انتظار/تصمیم‌گیری):**\n"
            f"  تعداد رسانه‌های در انتظار تأیید: {media_stats['pending_count']}\n"
            f"  تعداد رسانه‌های تأیید شده: {media_stats['approved_count']}\n"
            f"  تعداد رسانه‌های رد شده: {media_stats['rejected_count']}\n"
            "\n"
            "**آمار کاربران:**\n"
            f"  تعداد کل کاربران: {user_stats['total_users']}\n"
            f"  کاربران با نام سفارشی: {user_stats['custom_names']}\n"
            f"  کاربران با نام پیش‌فرض: {user_stats['default_names']}\n"
            f"  کل پیام‌های ارسالی توسط کاربران: {user_stats['total_messages']}"
        )
        await update.message.reply_text(stats_message, parse_mode='Markdown')
        logger.info(f"Admin {user_id} viewed stats.")

    async def admin_menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin menu with inline buttons"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if not self.config.is_admin(user_id):
            await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
            logger.warning(f"Non-admin user {user_id} tried to access admin menu.")
            return

        keyboard = [
            [InlineKeyboardButton("📊 آمار ربات", callback_data="admin_stats")],
            [InlineKeyboardButton("➕ افزودن کلمه توهین‌آمیز", callback_data="add_profanity_menu")],
            [InlineKeyboardButton("➖ حذف کلمه توهین‌آمیز", callback_data="remove_profanity_menu")],
            [InlineKeyboardButton("📄 لیست کلمات توهین‌آمیز", callback_data="list_profanity_menu")],
            [InlineKeyboardButton("⚙️ تنظیم فیلترینگ سختگیرانه", callback_data="set_strict_filtering_menu")],
            [InlineKeyboardButton("🚫 مدیریت بن", callback_data="ban_menu")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text("لطفاً یک گزینه ادمین را انتخاب کنید:", reply_markup=reply_markup)

    async def ban_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ban command to ban a user (admin only)"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if not self.config.is_admin(user_id):
            await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
            logger.warning(f"Non-admin user {user_id} tried to use /ban command.")
            return

        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("لطفاً User ID کاربر مورد نظر را وارد کنید. مثال: `/ban 12345`")
            return

        target_user_id = int(context.args[0])
        if self.user_manager.ban_user(target_user_id):
            await update.message.reply_text(f"کاربر {target_user_id} با موفقیت بن شد.")
            logger.info(f"Admin {user_id} banned user {target_user_id}.")
        else:
            await update.message.reply_text(f"کاربر {target_user_id} قبلاً بن شده بود یا خطایی رخ داد.")
            logger.warning(f"Admin {user_id} failed to ban user {target_user_id}.")

    async def unban_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unban command to unban a user (admin only)"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if not self.config.is_admin(user_id):
            await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
            logger.warning(f"Non-admin user {user_id} tried to use /unban command.")
            return

        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("لطفاً User ID کاربر مورد نظر را وارد کنید. مثال: `/unban 12345`")
            return

        target_user_id = int(context.args[0])
        if self.user_manager.unban_user(target_user_id):
            await update.message.reply_text(f"کاربر {target_user_id} با موفقیت از بن خارج شد.")
            logger.info(f"Admin {user_id} unbanned user {target_user_id}.")
        else:
            await update.message.reply_text(f"کاربر {target_user_id} قبلاً بن نبود یا خطایی رخ داد.")
            logger.warning(f"Admin {user_id} failed to unban user {target_user_id}.")

    async def check_ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check_ban command to check ban status of a user (admin only)"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if not self.config.is_admin(user_id):
            await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
            logger.warning(f"Non-admin user {user_id} tried to use /check_ban command.")
            return

        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("لطفاً User ID کاربر مورد نظر را وارد کنید. مثال: `/check_ban 12345`")
            return

        target_user_id = int(context.args[0])
        if self.user_manager.is_user_banned(target_user_id):
            await update.message.reply_text(f"کاربر {target_user_id} بن شده است.")
        else:
            await update.message.reply_text(f"کاربر {target_user_id} بن نشده است.")

        logger.info(f"Admin {user_id} checked ban status for user {target_user_id}.")


    #region New Profanity Filter Admin Commands (Added to fix missing attributes)

    # Added: Handler for /cancel
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command to cancel any ongoing operation."""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        # Reset any user state that might be active (e.g., setting name)
        if self.user_manager.is_user_setting_name_mode(user_id):
            self.user_manager.set_user_setting_name_mode(user_id, False)
            await update.message.reply_text("عملیات تنظیم نام لغو شد.")
            logger.info(f"User {user_id} cancelled name setting operation.")
            return

        # Here you can add logic to cancel other ongoing operations if any
        await update.message.reply_text("هیچ عملیات فعالی برای لغو وجود ندارد.")
        logger.info(f"User {user_id} sent /cancel command.")

    # Added: Handler for /add_profanity
    async def add_profanity_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_profanity command (admin only)"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if not self.config.is_admin(user_id):
            await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
            return

        if len(context.args) < 2:
            await update.message.reply_text("لطفاً زبان و کلمه را وارد کنید. مثال: `/add_profanity fa کلمه`")
            return

        language = context.args[0].lower()
        word = " ".join(context.args[1:])

        self.profanity_filter.add_word(word, language)
        await update.message.reply_text(f"کلمه '{word}' با موفقیت به لیست '{language}' اضافه شد.")
        logger.info(f"Admin {user_id} added profanity word: '{word}' in '{language}'.")

    # Added: Handler for /remove_profanity
    async def remove_profanity_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /remove_profanity command (admin only)"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if not self.config.is_admin(user_id):
            await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
            return

        if len(context.args) < 2:
            await update.message.reply_text("لطفاً زبان و کلمه را وارد کنید. مثال: `/remove_profanity fa کلمه`")
            return

        language = context.args[0].lower()
        word = " ".join(context.args[1:])

        if self.profanity_filter.remove_word(word, language):
            await update.message.reply_text(f"کلمه '{word}' با موفقیت از لیست '{language}' حذف شد.")
            logger.info(f"Admin {user_id} removed profanity word: '{word}' from '{language}'.")
        else:
            await update.message.reply_text(f"کلمه '{word}' در لیست '{language}' یافت نشد.")
            logger.warning(f"Admin {user_id} tried to remove non-existent profanity word: '{word}' in '{language}'.")

    # Added: Handler for /list_profanity
    async def list_profanity_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list_profanity command (admin only)"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if not self.config.is_admin(user_id):
            await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
            return

        if not context.args:
            await update.message.reply_text("لطفاً زبانی را برای لیست کردن کلمات وارد کنید. مثال: `/list_profanity fa`")
            return

        language = context.args[0].lower()
        words = self.profanity_filter.get_words(language)

        if words:
            word_list = "\\n".join(words)
            await update.message.reply_text(f"کلمات توهین‌آمیز در '{language}':\\n`{word_list}`", parse_mode='Markdown')
            logger.info(f"Admin {user_id} listed profanity words for '{language}'.")
        else:
            await update.message.reply_text(f"هیچ کلمه توهین‌آمیزی برای زبان '{language}' یافت نشد.")
            logger.warning(f"Admin {user_id} tried to list profanity words for non-existent language '{language}'.")


    # Added: Handler for /set_strict_filtering
    async def set_strict_filtering_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set_strict_filtering command (admin only)"""
        user_id = update.effective_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if not self.config.is_admin(user_id):
            await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
            return

        if not context.args or len(context.args) < 1:
            await update.message.reply_text("لطفاً وضعیت را وارد کنید (true/false). مثال: `/set_strict_filtering true`")
            return

        value = context.args[0].lower()
        if value == 'true':
            self.profanity_filter.set_strict_filtering(True) # Assume this method exists or needs to be added to ProfanityFilter
            await update.message.reply_text("فیلترینگ سختگیرانه فعال شد.")
            logger.info(f"Admin {user_id} set strict filtering to True.")
        elif value == 'false':
            self.profanity_filter.set_strict_filtering(False) # Assume this method exists or needs to be added to ProfanityFilter
            await update.message.reply_text("فیلترینگ سختگیرانه غیرفعال شد.")
            logger.info(f"Admin {user_id} set strict filtering to False.")
        else:
            await update.message.reply_text("ورودی نامعتبر. لطفاً 'true' یا 'false' وارد کنید.")

    #endregion


    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        user = update.effective_user
        if not user or not update.message or not update.message.text:
            return

        user_id = user.id
        message_text = update.message.text
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if self.user_manager.is_user_banned(user_id):
            await update.message.reply_text("شما از استفاده از ربات منع شده‌اید.")
            logger.warning(f"Banned user {user_id} sent text message: {message_text[:50]}...")
            return

        # Check if user is in name setting mode
        if self.user_manager.is_user_setting_name_mode(user_id):
            await self._set_user_display_name(update, context, message_text)
            return

        # Profanity filter check
        if self.profanity_filter.contains_profanity(message_text):
            await update.message.reply_text("پیام شما حاوی کلمات نامناسب است و نمی‌تواند به کانال ارسال شود. لطفاً متن را ویرایش کنید.")
            self.stats["messages_filtered"] += 1
            logger.info(f"Message from user {user_id} filtered due to profanity: {message_text[:50]}...")
            return

        # Forward to channel or for approval
        user_profile = self.user_manager.get_user_profile(user_id)
        display_name = user_profile.display_name if user_profile else user.username or user.first_name or "کاربر ناشناس"

        caption_to_post = f"ارسالی از: {display_name}\n\n{message_text}"

        if self.config.ADMIN_USER_ID: # If admin approval is enabled
            await self._send_message_for_approval(update, context, message_text, user_id, display_name)
        else: # Post directly if no admin approval needed
            try:
                await context.bot.send_message(
                    chat_id=self.config.CHANNEL_ID,
                    text=caption_to_post
                )
                await update.message.reply_text("پیام شما با موفقیت به کانال ارسال شد.")
                self.stats["messages_posted"] += 1
                logger.info(f"Text message from {user_id} posted directly to channel.")
            except TelegramError as e:
                logger.error(f"Failed to post text message to channel: {e}")
                await update.message.reply_text("خطا در ارسال پیام به کانال. لطفاً بعداً دوباره امتحان کنید.")


    async def handle_media_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming media messages (photo, video, document, etc.)"""
        user = update.effective_user
        if not user or not update.message:
            return

        user_id = user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if self.user_manager.is_user_banned(user_id):
            await update.message.reply_text("شما از استفاده از ربات منع شده‌اید.")
            logger.warning(f"Banned user {user_id} sent media message.")
            return

        # Check if user is in name setting mode (should not happen for media, but for safety)
        if self.user_manager.is_user_setting_name_mode(user_id):
            await update.message.reply_text("لطفاً ابتدا نام نمایشی خود را تکمیل کنید یا /cancel را بزنید.")
            return

        media_type = None
        file_id = None
        caption = update.message.caption or ""

        if update.message.photo:
            media_type = "photo"
            file_id = update.message.photo[-1].file_id # Get the largest photo
        elif update.message.video:
            media_type = "video"
            file_id = update.message.video.file_id
        elif update.message.document:
            media_type = "document"
            file_id = update.message.document.file_id
        elif update.message.audio:
            media_type = "audio"
            file_id = update.message.audio.file_id
        elif update.message.voice:
            media_type = "voice"
            file_id = update.message.voice.file_id
        elif update.message.animation:
            media_type = "animation"
            file_id = update.message.animation.file_id
        elif update.message.sticker:
            media_type = "sticker"
            file_id = update.message.sticker.file_id # Stickers usually don't have captions or need filtering
            # You might want to skip stickers from profanity check or approval workflow
            await update.message.reply_text("استیکرها به کانال ارسال نمی‌شوند.")
            logger.info(f"User {user_id} sent a sticker. Skipping.")
            return
        else:
            await update.message.reply_text("نوع رسانه پشتیبانی نمی‌شود.")
            logger.warning(f"Unsupported media type received from user {user_id}.")
            return

        if not media_type or not file_id:
            await update.message.reply_text("خطا در شناسایی فایل رسانه.")
            logger.error(f"Could not identify media type or file_id for message {update.message.message_id} from user {user_id}.")
            return

        # Profanity filter check for caption
        if self.profanity_filter.contains_profanity(caption):
            await update.message.reply_text("کپشن شما حاوی کلمات نامناسب است و نمی‌تواند به کانال ارسال شود. لطفاً کپشن را ویرایش کنید یا پیام را بدون کپشن ارسال کنید.")
            self.stats["messages_filtered"] += 1
            logger.info(f"Media caption from user {user_id} filtered due to profanity: {caption[:50]}...")
            return

        user_profile = self.user_manager.get_user_profile(user_id)
        username = user_profile.telegram_username if user_profile else user.username or user.first_name or "Unknown"

        if self.config.ADMIN_USER_ID: # If admin approval is enabled
            # Add media to pending queue
            pending_id = self.media_manager.add_pending_media(
                user_id=user_id,
                username=username,
                message_id=update.message.message_id,
                media_type=media_type,
                file_id=file_id,
                caption=caption
            )
            self.stats["media_pending"] += 1
            if pending_id:
                await update.message.reply_text("رسانه شما برای بررسی ارسال شد. پس از تأیید در کانال منتشر خواهد شد.")
                logger.info(f"Media {pending_id} from user {user_id} added to pending queue.")
                # Notify admin
                await self._send_media_for_approval(pending_id, update, context)
            else:
                await update.message.reply_text("متاسفانه در حال حاضر رسانه‌های زیادی در صف انتظار هستند. لطفاً بعداً امتحان کنید.")
                logger.warning(f"Failed to add media for user {user_id} to pending queue. Queue full?")
        else: # Post directly if no admin approval needed
            try:
                await self._send_media_to_channel(
                    context, self.config.CHANNEL_ID, update.message.message_id,
                    media_type, file_id, caption, user_id, username
                )
                await update.message.reply_text("رسانه شما با موفقیت به کانال ارسال شد.")
                self.stats["messages_posted"] += 1
                logger.info(f"Media from {user_id} posted directly to channel.")
            except TelegramError as e:
                logger.error(f"Failed to post media to channel: {e}")
                await update.message.reply_text("خطا در ارسال رسانه به کانال. لطفاً بعداً دوباره امتحان کنید.")


    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        user_id = query.from_user.id
        self.user_manager.increment_message_count(user_id)
        self.stats["messages_processed"] += 1

        if not self.config.is_admin(user_id):
            try:
                await query.answer("شما اجازه دسترسی به این عملکرد را ندارید.", show_alert=True)
            except TelegramError as e:
                logger.error(f"Failed to answer unauthorized callback query: {e}")
            logger.warning(f"Non-admin user {user_id} tried to use admin button: {query.data}.")
            return

        try:
            await query.answer() # Acknowledge the callback query
        except TelegramError as e:
            logger.error(f"Failed to answer callback query: {e}")
            # Even if answer fails, try to continue with the logic, as the user might have already seen the pop-up

        data = query.data
        logger.info(f"Admin {user_id} pressed button: {data}")

        if data.startswith("approve_"):
            media_id = data.split("_")[1]
            await self._handle_media_approval(media_id, True, user_id, context, query.message.message_id)
        elif data.startswith("reject_"):
            media_id = data.split("_")[1]
            await self._handle_media_approval(media_id, False, user_id, context, query.message.message_id)
        elif data == "set_name":
            # This is a user command from main menu
            # Instead of calling set_name_command directly with query, use query.message for reply context
            # Or, better, redirect to the command logic
            await self.set_name_command(update, context) # Re-use the command handler logic
        elif data == "admin_stats":
            # This is an admin command from main menu
            await self.admin_stats_command(update, context) # Re-use the command handler logic
        elif data == "admin_menu":
            await self.admin_menu_command(update, context)
        elif data == "ban_menu":
            # Show a sub-menu for ban management (e.g., provide user ID)
            await query.edit_message_text(
                "لطفاً دستورات بن را مستقیماً وارد کنید: /ban [user_id], /unban [user_id], /check_ban [user_id]",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی ادمین", callback_data="admin_menu")]])
            )
        elif data == "main_menu":
            await self.show_main_menu(update, context)
        elif data == "add_profanity_menu":
             await query.edit_message_text(
                "برای افزودن کلمه توهین‌آمیز: `/add_profanity [lang] [word]`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی ادمین", callback_data="admin_menu")]])
            )
        elif data == "remove_profanity_menu":
             await query.edit_message_text(
                "برای حذف کلمه توهین‌آمیز: `/remove_profanity [lang] [word]`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی ادمین", callback_data="admin_menu")]])
            )
        elif data == "list_profanity_menu":
             await query.edit_message_text(
                "برای لیست کلمات توهین‌آمیز: `/list_profanity [lang]`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی ادمین", callback_data="admin_menu")]])
            )
        elif data == "set_strict_filtering_menu":
             await query.edit_message_text(
                "برای تنظیم فیلترینگ سختگیرانه: `/set_strict_filtering [true/false]`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی ادمین", callback_data="admin_menu")]])
            )
        else:
            await query.edit_message_text("گزینه نامعتبر.")

    async def _send_message_for_approval(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                        message_text: str, user_id: int, display_name: str):
        """Send text message to admin for approval"""
        pending_id = self.media_manager.add_pending_media(
            user_id=user_id,
            username=display_name, # Using display_name here
            message_id=update.message.message_id,
            media_type="text",
            file_id=None, # No file_id for text
            caption=message_text # Text message content is the caption here
        )
        self.stats["media_pending"] += 1
        if pending_id:
            await update.message.reply_text("پیام متنی شما برای بررسی ارسال شد. پس از تأیید در کانال منتشر خواهد شد.")
            logger.info(f"Text message {pending_id} from user {user_id} added to pending queue.")

            # Construct message for admin
            approval_text = (
                f"**پیام متنی جدید برای تأیید:**\n"
                f"**از طرف:** {display_name} (ID: {user_id})\n"
                f"**محتوا:**\n"
                f"```\n{message_text}\n```"
            )

            keyboard = [
                [InlineKeyboardButton("✅ تأیید", callback_data=f"approve_{pending_id}"),
                 InlineKeyboardButton("❌ رد", callback_data=f"reject_{pending_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.send_message(
                    chat_id=self.config.ADMIN_USER_ID,
                    text=approval_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except TelegramError as e:
                logger.error(f"Failed to send text approval message to admin {self.config.ADMIN_USER_ID}: {e}")
                await update.message.reply_text("خطا در ارسال پیام برای ادمین. لطفاً بعداً دوباره امتحان کنید.")
        else:
            await update.message.reply_text("متاسفانه در حال حاضر پیام‌های زیادی در صف انتظار هستند. لطفاً بعداً امتحان کنید.")
            logger.warning(f"Failed to add text message for user {user_id} to pending queue. Queue full?")


    async def _send_media_for_approval(self, pending_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send media to admin for approval"""
        media_item = self.media_manager.get_media_item(pending_id)
        if not media_item:
            logger.error(f"Media item {pending_id} not found for approval.")
            return

        user_profile = self.user_manager.get_user_profile(media_item.user_id)
        display_name = user_profile.display_name if user_profile else media_item.username

        # Construct caption for admin
        admin_caption = (
            f"**رسانه جدید برای تأیید:**\n"
            f"**از طرف:** {display_name} (ID: {media_item.user_id})\n"
            f"**نوع:** {media_item.media_type}\n"
            f"**کپشن اصلی:** {media_item.caption or '_ندارد_'}"
        )

        keyboard = [
            [InlineKeyboardButton("✅ تأیید", callback_data=f"approve_{pending_id}"),
             InlineKeyboardButton("❌ رد", callback_data=f"reject_{pending_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            # Send the media itself
            if media_item.media_type == "photo":
                await context.bot.send_photo(
                    chat_id=self.config.ADMIN_USER_ID,
                    photo=media_item.file_id,
                    caption=admin_caption,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            elif media_item.media_type == "video":
                await context.bot.send_video(
                    chat_id=self.config.ADMIN_USER_ID,
                    video=media_item.file_id,
                    caption=admin_caption,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            elif media_item.media_type == "document":
                await context.bot.send_document(
                    chat_id=self.config.ADMIN_USER_ID,
                    document=media_item.file_id,
                    caption=admin_caption,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            elif media_item.media_type == "audio":
                await context.bot.send_audio(
                    chat_id=self.config.ADMIN_USER_ID,
                    audio=media_item.file_id,
                    caption=admin_caption,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            elif media_item.media_type == "voice":
                await context.bot.send_voice(
                    chat_id=self.config.ADMIN_USER_ID,
                    voice=media_item.file_id,
                    caption=admin_caption,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            elif media_item.media_type == "animation":
                await context.bot.send_animation(
                    chat_id=self.config.ADMIN_USER_ID,
                    animation=media_item.file_id,
                    caption=admin_caption,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                # Fallback for unsupported media types or if file_id is somehow missing for a text message
                await context.bot.send_message(
                    chat_id=self.config.ADMIN_USER_ID,
                    text=f"**رسانه جدید برای تأیید (نوع نامشخص):**\n{admin_caption}",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                logger.warning(f"Unsupported media type '{media_item.media_type}' for approval: {pending_id}")

        except TelegramError as e:
            logger.error(f"Failed to send media {pending_id} for approval to admin {self.config.ADMIN_USER_ID}: {e}")
            await update.message.reply_text("خطا در ارسال رسانه برای ادمین جهت تأیید. لطفاً بعداً دوباره امتحان کنید.")


    async def _handle_media_approval(self, media_id: str, approved: bool, admin_id: int, context: ContextTypes.DEFAULT_TYPE, admin_message_id: int):
        """Handle admin approval/rejection of media"""
        media_item = self.media_manager.get_media_item(media_id)
        if not media_item:
            logger.error(f"Media item {media_id} not found for approval decision.")
            # Try to edit the admin's message to reflect that it's no longer valid
            try:
                await context.bot.edit_message_text(
                    chat_id=self.config.ADMIN_USER_ID,
                    message_id=admin_message_id,
                    text="❌ این رسانه قبلاً پردازش شده یا یافت نشد."
                )
            except TelegramError as e:
                logger.warning(f"Failed to edit admin message {admin_message_id}: {e}")
            return

        # Mark media as approved/rejected in media manager
        self.media_manager.set_media_decision(media_id, approved, admin_id)
        
        # Update stats
        if approved:
            self.stats["media_approved"] += 1
        else:
            self.stats["media_rejected"] += 1

        # Inform the original user
        user_profile = self.user_manager.get_user_profile(media_item.user_id)
        display_name = user_profile.display_name if user_profile else media_item.username

        if approved:
            try:
                # Send to channel
                await self._send_media_to_channel(
                    context, self.config.CHANNEL_ID, media_item.message_id,
                    media_item.media_type, media_item.file_id, media_item.caption, media_item.user_id, display_name
                )
                await context.bot.send_message(
                    chat_id=media_item.user_id,
                    text="✅ رسانه شما تأیید و در کانال منتشر شد."
                )
                self.stats["messages_posted"] += 1
                logger.info(f"Media {media_id} from user {media_item.user_id} approved and posted.")
            except TelegramError as e:
                logger.error(f"Failed to post media {media_id} to channel or notify user: {e}")
                await context.bot.send_message(
                    chat_id=media_item.user_id,
                    text="❌ رسانه شما تأیید شد اما در ارسال به کانال خطایی رخ داد."
                )
        else:
            try:
                await context.bot.send_message(
                    chat_id=media_item.user_id,
                    text="❌ رسانه شما رد شد."
                )
                logger.info(f"Media {media_id} from user {media_item.user_id} rejected.")
            except TelegramError as e:
                logger.error(f"Failed to notify user {media_item.user_id} about media rejection: {e}")

        # Edit admin's original message to show decision
        decision_text = "✅ تأیید شده" if approved else "❌ رد شده"
        try:
            # Retrieve the original message text if possible, and append the decision
            original_message_text = "متن پیام اصلی در دسترس نیست."
            if context.bot.get_chat_member: # Check if bot API supports get_chat_member
                 # This is tricky as we don't have the message content here, only the ID.
                 # For simplicity, just update with a generic message for now or pass original text.
                 pass

            # Update the message that admin interacted with
            updated_caption = f"~~{media_item.caption or 'بدون کپشن'}~~\n\n**{decision_text}** توسط ادمین {admin_id}."
            await context.bot.edit_message_caption(
                chat_id=self.config.ADMIN_USER_ID,
                message_id=admin_message_id,
                caption=updated_caption,
                parse_mode='Markdown',
                reply_markup=None # Remove buttons after decision
            )
            # If it's a text message, edit message text instead of caption
            if media_item.media_type == "text":
                 # Need to reconstruct the original message sent to admin
                 original_admin_text = (
                    f"**پیام متنی جدید برای تأیید:**\n"
                    f"**از طرف:** {display_name} (ID: {media_item.user_id})\n"
                    f"**محتوا:**\n"
                    f"```\n{media_item.caption}\n```" # For text, caption is the content
                )
                 await context.bot.edit_message_text(
                    chat_id=self.config.ADMIN_USER_ID,
                    message_id=admin_message_id,
                    text=f"{original_admin_text}\n\n**{decision_text}** توسط ادمین {admin_id}.",
                    parse_mode='Markdown',
                    reply_markup=None
                 )

        except TelegramError as e:
            logger.error(f"Failed to edit admin message {admin_message_id} after decision: {e}")

        # Clean up processed media from pending list (if desired, based on previous discussion)
        self.media_manager.remove_processed_media(media_id)


    async def _send_media_to_channel(self, context: ContextTypes.DEFAULT_TYPE, chat_id: str, original_message_id: int,
                                    media_type: str, file_id: str, caption: str, user_id: int, display_name: str):
        """Internal method to send media to a target channel/chat"""
        final_caption = f"ارسالی از: {display_name}\n\n{caption}"

        if media_type == "photo":
            await context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=final_caption)
        elif media_type == "video":
            await context.bot.send_video(chat_id=chat_id, video=file_id, caption=final_caption)
        elif media_type == "document":
            await context.bot.send_document(chat_id=chat_id, document=file_id, caption=final_caption)
        elif media_type == "audio":
            await context.bot.send_audio(chat_id=chat_id, audio=file_id, caption=final_caption)
        elif media_type == "voice":
            await context.bot.send_voice(chat_id=chat_id, voice=file_id, caption=final_caption)
        elif media_type == "animation":
            await context.bot.send_animation(chat_id=chat_id, animation=file_id, caption=final_caption)
        elif media_type == "text":
            await context.bot.send_message(chat_id=chat_id, text=final_caption)
        else:
            logger.error(f"Attempted to send unsupported media type '{media_type}' to channel.")
            # Fallback to sending just the caption as a message
            await context.bot.send_message(chat_id=chat_id, text=f"رسانه با فرمت نامشخص:\\n{final_caption}")


    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a telegram message to notify the developer."""
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

        # traceback.format_exception returns a list of strings, which may not always
        # be desirable.
        # traceback_text = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
        # update_str = update.to_dict() if isinstance(update, Update) else str(update)
        # message_to_admin = (
        #     f"An exception was raised while handling an update:\n"
        #     f"<pre>update = {html.escape(json.dumps(update_str, indent=2))}</pre>\n\n"
        #     f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        #     f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        #     f"<pre>{html.escape(traceback_text)}</pre>"
        # )

        # For simplicity, send a basic error message
        error_message_to_admin = f"🚨 **خطا در ربات!** 🚨\\n\\n`{context.error}`\\n\\nبرای جزئیات بیشتر لاگ‌ها را بررسی کنید."

        if self.config.ADMIN_USER_ID:
            try:
                await context.bot.send_message(
                    chat_id=self.config.ADMIN_USER_ID,
                    text=error_message_to_admin,
                    parse_mode='Markdown'
                )
            except TelegramError as e:
                logger.error(f"Failed to send error message to admin {self.config.ADMIN_USER_ID}: {e}")

        # Optionally, send a general message to the user who caused the error
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "متاسفانه خطایی در پردازش درخواست شما رخ داد. لطفاً بعداً امتحان کنید."
                )
            except TelegramError as e:
                logger.error(f"Failed to send error message to user {update.effective_user.id}: {e}")