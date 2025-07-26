"""
Telegram bot handlers for processing messages and commands
"""

import logging
import time
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

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
        
        # Create keyboard for name setting if not already set or if default
        keyboard = [
            [InlineKeyboardButton("تغییر نام مستعار ✏️", callback_data="set_name")]
        ]
        
        # Initial greeting text
        greeting_text = (
            f"سلام {user_profile.display_name} عزیز!\n"
            "به ربات فیلترکننده محتوای کانال خوش آمدید.\n"
            "شما می‌توانید پیام‌های متنی یا رسانه‌ای خود را به صورت ناشناس به کانال ارسال کنید."
        )
        
        if user_profile.display_name.startswith("کاربر شماره"):
            greeting_text += "\n\n" + "برای ارسال پیام، کافیست پیام خود را برای من بفرستید. همچنین می‌توانید با استفاده از دکمه زیر یک نام مستعار برای خود انتخاب کنید تا در کنار پیام‌های شما نمایش داده شود."
        else:
            greeting_text += "\n\n" + "برای ارسال پیام، کافیست پیام خود را برای من بفرستید."

        reply_markup = InlineKeyboardMarkup(keyboard) if user_profile.display_name.startswith("کاربر شماره") else None
        
        try:
            await update.message.reply_text(greeting_text, reply_markup=reply_markup)
            logger.info(f"User {user.id} started bot. Display name: {user_profile.display_name}")
        except TelegramError as e:
            logger.error(f"Error sending start message to user {user.id}: {e}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "راهنمای استفاده از ربات:\n"
            "- برای ارسال پیام متنی یا رسانه‌ای به کانال، کافیست آن را برای من ارسال کنید.\n"
            "- پیام‌های متنی بعد از بررسی فیلتر کلمات رکیک، به صورت ناشناس در کانال منتشر می‌شوند.\n"
            "- پیام‌های رسانه‌ای (عکس، ویدئو، صدا و غیره) ابتدا برای مدیر ارسال شده و پس از تأیید او منتشر خواهند شد.\n"
            "- برای تغییر نام مستعار خود از دستور /set_name استفاده کنید.\n"
            "- برای دیدن نام مستعار فعلی خود از دستور /my_name استفاده کنید."
        )
        try:
            await update.message.reply_text(help_text)
        except TelegramError as e:
            logger.error(f"Error sending help message to user {update.effective_user.id}: {e}")

    async def set_name_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set_name command"""
        user = update.effective_user
        if not user:
            return

        if self.config.is_admin(user.id):
            try:
                await update.message.reply_text("شما مدیر هستید و نیازی به تنظیم نام مستعار ندارید.")
            except TelegramError as e:
                logger.error(f"Error replying to admin {user.id} in set_name: {e}")
            return

        # Set user's state to "setting name" mode
        self.user_manager.set_user_setting_name_mode(user.id, True)

        try:
            await update.message.reply_text("لطفاً نام مستعار جدید خود را ارسال کنید. (مثال: علی)\n"
                                            "نام مستعار باید حداقل ۳ و حداکثر ۱۵ کاراکتر باشد و فقط شامل حروف فارسی یا انگلیسی و فاصله باشد.")
            logger.info(f"User {user.id} initiated set_name command.")
        except TelegramError as e:
            logger.error(f"Error sending set_name prompt to user {user.id}: {e}")

    async def my_name_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /my_name command"""
        user = update.effective_user
        if not user:
            return

        user_profile = self.user_manager.get_user_profile(user.id)
        try:
            if user_profile:
                await update.message.reply_text(f"نام مستعار فعلی شما: **{user_profile.display_name}**", parse_mode='Markdown')
            else:
                await update.message.reply_text("شما هنوز نام مستعاری ندارید. از دستور /start برای شروع استفاده کنید.")
        except TelegramError as e:
            logger.error(f"Error sending my_name response to user {user.id}: {e}")

    async def admin_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin_stats command - Admin only"""
        user = update.effective_user
        if not user or not self.config.is_admin(user.id):
            try:
                await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
            except TelegramError as e:
                logger.error(f"Error denying stats access to user {user.id}: {e}")
            return

        media_stats = self.media_manager.get_media_stats()
        user_stats = self.user_manager.get_user_stats()

        stats_text = (
            "📊 **آمار ربات:**\n"
            "--- پیام‌ها ---\n"
            f"✔️ پردازش شده: {self.stats['messages_processed']}\n"
            f"🚫 فیلتر شده (کلمات رکیک): {self.stats['messages_filtered']}\n"
            f"✅ پست شده در کانال: {self.stats['messages_posted']}\n"
            "--- رسانه‌ها ---\n"
            f"⏳ در انتظار تأیید: {media_stats['pending']}\n"
            f"👍 تأیید شده: {media_stats['approved']}\n"
            f"👎 رد شده: {media_stats['rejected']}\n"
            "--- کاربران ---\n"
            f"👥 کل کاربران: {user_stats['total_users']}\n"
            f"✏️ کاربران با نام مستعار سفارشی: {user_stats['custom_names']}\n"
            f"👤 کاربران با نام پیش‌فرض: {user_stats['default_names']}\n"
            f"💬 کل پیام‌های ارسال شده توسط کاربران: {user_stats['total_messages']}\n"
        )
        try:
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            logger.info(f"Admin {user.id} requested stats.")
        except TelegramError as e:
            logger.error(f"Error sending admin stats to admin {user.id}: {e}")

    async def add_profanity_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_profanity command - Admin only"""
        user = update.effective_user
        if not user or not self.config.is_admin(user.id):
            try:
                await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
            except TelegramError as e:
                logger.error(f"Error denying profanity add access to user {user.id}: {e}")
            return

        if not context.args:
            try:
                await update.message.reply_text("لطفاً کلمه رکیک مورد نظر و زبان آن را وارد کنید. مثال: `/add_profanity badword english` یا `/add_profanity کلمه_بد فارسی`")
            except TelegramError as e:
                logger.error(f"Error sending profanity add usage to admin {user.id}: {e}")
            return

        word = context.args[0]
        language = context.args[1] if len(context.args) > 1 else "persian" # Default to Persian

        if language not in ["english", "persian", "persian_latin"]:
            try:
                await update.message.reply_text("زبان نامعتبر است. زبان‌های پشتیبانی شده: `english`, `persian`, `persian_latin`")
            except TelegramError as e:
                logger.error(f"Error sending invalid language message to admin {user.id}: {e}")
            return

        self.profanity_filter.add_word(word, language)
        try:
            await update.message.reply_text(f"کلمه '{word}' به لیست کلمات رکیک '{language}' اضافه شد.")
            logger.info(f"Admin {user.id} added profanity word: '{word}' ({language})")
        except TelegramError as e:
            logger.error(f"Error confirming profanity add to admin {user.id}: {e}")
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Shows the main menu with options for users."""
        user = update.effective_user
        if not user:
            return

        keyboard = [
            [InlineKeyboardButton("تغییر نام مستعار ✏️", callback_data="set_name")],
            [InlineKeyboardButton("راهنما ❓", callback_data="help_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.message.reply_text("لطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup=reply_markup)
            logger.info(f"User {user.id} requested main menu.")
        except TelegramError as e:
            logger.error(f"Error sending main menu to user {user.id}: {e}")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles inline keyboard button presses."""
        query = update.callback_query
        try:
            await query.answer() # Acknowledge the query
        except TelegramError as e:
            logger.error(f"Error answering callback query from {query.from_user.id}: {e}")
            # Even if answer fails, try to proceed with the action

        user_id = query.from_user.id
        data = query.data

        if data.startswith("approve_media_"):
            media_id = data.replace("approve_media_", "")
            await self._handle_media_approval(query, context, media_id, True)
        elif data.startswith("reject_media_"):
            media_id = data.replace("reject_media_", "")
            await self._handle_media_approval(query, context, media_id, False)
        elif data == "set_name":
            # This is called when user presses "تغییر نام مستعار" button
            # We need to create a dummy message object for set_name_command if it expects one
            # Alternatively, refactor set_name_command to accept a query directly
            # For simplicity, let's pass the update.callback_query object itself if it works.
            # If not, a small wrapper might be needed.
            # Given that set_name_command uses update.message, it's safer to call it via a message simulation or refactor.
            # For now, let's assume it can handle query if relevant parts are `query.message`
            # Re-calling set_name_command:
            await self.set_name_command(query, context)
        elif data == "help_menu":
            # Re-calling help_command
            await self.help_command(query, context)
        else:
            logger.warning(f"Unknown callback query data: {data} from user {user_id}")


    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages."""
        user = update.effective_user
        if not user or not update.message or not update.message.text:
            return

        self.stats['messages_processed'] += 1
        self.user_manager.increment_message_count(user.id)
        
        text = update.message.text
        user_profile = self.user_manager.get_user_profile(user.id)

        # Check if user is in name setting mode
        if self.user_manager.is_user_setting_name_mode(user.id):
            await self._set_user_display_name(update, context, user, text)
            return

        # Profanity check
        has_profanity, found_words = self.profanity_filter.contains_profanity(text)

        if has_profanity:
            self.stats['messages_filtered'] += 1
            try:
                await update.message.reply_text(
                    f"متاسفانه پیام شما حاوی کلمات نامناسب ({', '.join(found_words)}) بود و قابل انتشار نیست."
                )
                logger.info(f"Filtered message from {user.id} due to profanity: {text}")
            except TelegramError as e:
                logger.error(f"Error sending profanity filter message to user {user.id}: {e}")
            return

        # Post to channel
        display_name = user_profile.display_name if user_profile else "ناشناس"
        message_to_post = f"{text}\n\n**از طرف:** {display_name}"
        
        try:
            await context.bot.send_message(
                chat_id=self.config.CHANNEL_ID,
                text=message_to_post,
                parse_mode='Markdown'
            )
            self.stats['messages_posted'] += 1
            await update.message.reply_text("پیام شما با موفقیت به کانال ارسال شد.")
            logger.info(f"Posted text message from {user.id} to channel: {text}")
        except TelegramError as e:
            await update.message.reply_text("متاسفانه در ارسال پیام شما به کانال خطایی رخ داد.")
            logger.error(f"Error posting text message to channel for user {user.id}: {e}")
            
    async def _set_user_display_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: UserProfile, new_name: str):
        """Internal helper to set user display name."""
        
        # Validate name length and content
        if not (3 <= len(new_name) <= 15) or not self.profanity_filter.is_valid_name(new_name):
            try:
                await update.message.reply_text(
                    "نام مستعار نامعتبر است. نام مستعار باید حداقل ۳ و حداکثر ۱۵ کاراکتر باشد و فقط شامل حروف فارسی یا انگلیسی و فاصله باشد."
                )
            except TelegramError as e:
                logger.error(f"Error sending invalid name length/content error to user {user.id}: {e}")
            return

        # Profanity check for the new name
        has_profanity_in_name, _ = self.profanity_filter.contains_profanity(new_name)
        if has_profanity_in_name:
            try:
                await update.message.reply_text(
                    "متاسفانه نام مستعار انتخابی شما حاوی کلمات نامناسب است. لطفاً نام دیگری انتخاب کنید."
                )
            except TelegramError as e:
                logger.error(f"Error sending profanity in name error to user {user.id}: {e}")
            return

        # Attempt to set name
        success = self.user_manager.set_display_name(user.id, new_name)
        
        if success:
            try:
                await update.message.reply_text(f"نام مستعار شما با موفقیت به **{new_name}** تغییر یافت.", parse_mode='Markdown')
                logger.info(f"User {user.id} successfully set display name to {new_name}")
                self.user_manager.set_user_setting_name_mode(user.id, False) # Exit name setting mode
            except TelegramError as e:
                logger.error(f"Error confirming successful name change to user {user.id}: {e}")
        else:
            try:
                await update.message.reply_text("این نام مستعار قبلاً استفاده شده است. لطفاً نام دیگری انتخاب کنید.")
                logger.warning(f"User {user.id} failed to set display name to {new_name} (already taken)")
                # Do not exit setting name mode if name is taken, let user try again
            except TelegramError as e:
                logger.error(f"Error informing user {user.id} about taken name: {e}")

    async def handle_media_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming media messages."""
        user = update.effective_user
        if not user or not update.message:
            return

        self.user_manager.increment_message_count(user.id)
        
        # Admins can bypass approval
        if self.config.is_admin(user.id):
            logger.info(f"Admin {user.id} sent media, bypassing approval.")
            try:
                # Get the display name for the admin's post
                user_profile = self.user_manager.get_user_profile(user.id)
                display_name = user_profile.display_name if user_profile else "مدیر" # Fallback for admin
                
                # Forward the message directly to the channel
                await context.bot.forward_message(
                    chat_id=self.config.CHANNEL_ID,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
                # Append sender info as a separate message or edit caption if possible (more complex)
                await context.bot.send_message(
                    chat_id=self.config.CHANNEL_ID,
                    text=f"**از طرف:** {display_name}",
                    parse_mode='Markdown'
                )
                await update.message.reply_text("پیام رسانه‌ای شما به عنوان مدیر، مستقیماً به کانال ارسال شد.")
                self.stats['media_approved'] += 1 # Count as approved immediately
            except TelegramError as e:
                logger.error(f"Error forwarding admin media for admin {user.id}: {e}")
                await update.message.reply_text("خطا در ارسال پیام رسانه‌ای شما به کانال.")
            return

        # Only process if there's actual media
        media_type = None
        file_id = None
        caption = update.message.caption or ""

        if update.message.photo:
            media_type = "photo"
            file_id = update.message.photo[-1].file_id # Get largest photo
        elif update.message.video:
            media_type = "video"
            file_id = update.message.video.file_id
        elif update.message.audio:
            media_type = "audio"
            file_id = update.message.audio.file_id
        elif update.message.voice:
            media_type = "voice"
            file_id = update.message.voice.file_id
        elif update.message.document:
            media_type = "document"
            file_id = update.message.document.file_id
        elif update.message.animation:
            media_type = "animation"
            file_id = update.message.animation.file_id
        elif update.message.sticker:
            media_type = "sticker"
            file_id = update.message.sticker.file_id
        # Add other media types as needed

        if not media_type or not file_id:
            try:
                await update.message.reply_text("لطفاً یک فایل رسانه‌ای (عکس، ویدئو، صدا، سند، استیکر یا انیمیشن) ارسال کنید.")
            except TelegramError as e:
                logger.error(f"Error telling user {user.id} to send media: {e}")
            return
            
        # Check if media queue is full
        if self.media_manager.get_pending_media_count() >= self.config.MAX_PENDING_MEDIA:
            try:
                await update.message.reply_text("صف تأیید رسانه‌ها پر است. لطفاً بعداً امتحان کنید.")
                logger.warning(f"Media queue full, rejected media from {user.id}")
            except TelegramError as e:
                logger.error(f"Error telling user {user.id} about full media queue: {e}")
            return

        # Check caption for profanity
        if caption:
            has_profanity_in_caption, _ = self.profanity_filter.contains_profanity(caption)
            if has_profanity_in_caption:
                try:
                    await update.message.reply_text("کپشن شما حاوی کلمات نامناسب است و قابل ارسال نیست.")
                    self.stats['messages_filtered'] += 1 # Count filtered captions
                    logger.info(f"Filtered media from {user.id} due to profanity in caption: {caption}")
                except TelegramError as e:
                    logger.error(f"Error telling user {user.id} about profanity in caption: {e}")
                return

        # Add media to pending list
        media_id = self.media_manager.add_pending_media(
            user_id=user.id,
            username=user.username or user.first_name or "Unknown",
            message_id=update.message.message_id,
            media_type=media_type,
            file_id=file_id,
            caption=caption
        )
        self.stats['media_pending'] += 1

        try:
            await update.message.reply_text("پیام رسانه‌ای شما برای تأیید به مدیر ارسال شد. پس از تأیید، در کانال منتشر خواهد شد.")
            await self._send_media_for_approval(media_id, update, context)
            logger.info(f"Media {media_id} from {user.id} submitted for approval.")
        except TelegramError as e:
            logger.error(f"Error confirming media submission to user {user.id}: {e}")

    async def _send_media_for_approval(self, media_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Internal helper to send media to admin for approval."""
        media = self.media_manager.get_pending_media_by_id(media_id)
        if not media:
            logger.error(f"Media {media_id} not found for approval sending.")
            return

        user_profile = self.user_manager.get_user_profile(media.user_id)
        display_name = user_profile.display_name if user_profile else "ناشناس"

        approval_text = (
            f"**رسانه جدید برای تأیید:**\n"
            f"**از طرف:** {display_name} (ID: `{media.user_id}`)\n"
            f"**زمان ارسال:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(media.timestamp))}\n"
            f"**نوع رسانه:** {media.media_type}\n"
            f"**کپشن:** {media.caption or '_ندارد_'}\n\n"
            f"آیا این رسانه را تأیید می‌کنید؟"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ تأیید", callback_data=f"approve_media_{media_id}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_media_{media_id}")
            ]
        ])

        try:
            # Send the actual media file
            if media.media_type == "photo":
                await context.bot.send_photo(
                    chat_id=self.config.ADMIN_USER_ID,
                    photo=media.file_id,
                    caption=media.caption # Keep original caption for admin review
                )
            elif media.media_type == "video":
                await context.bot.send_video(
                    chat_id=self.config.ADMIN_USER_ID,
                    video=media.file_id,
                    caption=media.caption
                )
            elif media.media_type == "audio":
                await context.bot.send_audio(
                    chat_id=self.config.ADMIN_USER_ID,
                    audio=media.file_id,
                    caption=media.caption
                )
            elif media.media_type == "voice":
                await context.bot.send_voice(
                    chat_id=self.config.ADMIN_USER_ID,
                    voice=media.file_id,
                    caption=media.caption
                )
            elif media.media_type == "document":
                await context.bot.send_document(
                    chat_id=self.config.ADMIN_USER_ID,
                    document=media.file_id,
                    caption=media.caption
                )
            elif media.media_type == "animation":
                await context.bot.send_animation(
                    chat_id=self.config.ADMIN_USER_ID,
                    animation=media.file_id,
                    caption=media.caption
                )
            elif media.media_type == "sticker":
                await context.bot.send_sticker(
                    chat_id=self.config.ADMIN_USER_ID,
                    sticker=media.file_id
                )
            
            # Send approval message
            await context.bot.send_message(
                chat_id=self.config.ADMIN_USER_ID,
                text=approval_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
            logger.info(f"Sent media {media_id} to admin for approval")
            
        except TelegramError as e:
            logger.error(f"Error sending media {media_id} for approval to admin: {e}")
            # Optionally notify the user about the failure to send for approval
            try:
                await context.bot.send_message(
                    chat_id=media.user_id,
                    text="متاسفانه، به دلیل خطای فنی، پیام رسانه‌ای شما برای تأیید مدیر ارسال نشد. لطفاً بعداً دوباره تلاش کنید."
                )
            except TelegramError as user_e:
                logger.error(f"Failed to notify user {media.user_id} about media submission error: {user_e}")

    async def _handle_media_approval(self, query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE, media_id: str, approved: bool):
        """Internal helper to handle media approval/rejection."""
        admin_id = query.from_user.id
        if not self.config.is_admin(admin_id):
            try:
                await query.answer("شما اجازه انجام این عملیات را ندارید.", show_alert=True)
            except TelegramError as e:
                logger.error(f"Error answering unauthorized admin query from {admin_id}: {e}")
            return

        media = self.media_manager.get_pending_media_by_id(media_id)
        if not media:
            try:
                await query.edit_message_text("این رسانه قبلاً پردازش شده یا یافت نشد.")
                logger.warning(f"Media {media_id} not found for approval decision by admin {admin_id}.")
            except TelegramError as e:
                logger.error(f"Error editing message for missing media {media_id} by admin {admin_id}: {e}")
            return

        action_text = "تأیید" if approved else "رد"
        
        # Update media status
        self.media_manager.update_media_status(media_id, approved, admin_id)
        
        if approved:
            self.stats['media_approved'] += 1
            self.stats['media_pending'] -= 1
            # Post to channel
            user_profile = self.user_manager.get_user_profile(media.user_id)
            display_name = user_profile.display_name if user_profile else "ناشناس"
            
            caption_to_post = media.caption
            # Add "by" line to caption if there's an existing caption, otherwise create it as caption
            if caption_to_post:
                caption_to_post += f"\n\n**از طرف:** {display_name}"
            else:
                caption_to_post = f"**از طرف:** {display_name}"

            try:
                # Send the media to the channel
                if media.media_type == "photo":
                    await context.bot.send_photo(
                        chat_id=self.config.CHANNEL_ID,
                        photo=media.file_id,
                        caption=caption_to_post,
                        parse_mode='Markdown'
                    )
                elif media.media_type == "video":
                    await context.bot.send_video(
                        chat_id=self.config.CHANNEL_ID,
                        video=media.file_id,
                        caption=caption_to_post,
                        parse_mode='Markdown'
                    )
                elif media.media_type == "audio":
                    await context.bot.send_audio(
                        chat_id=self.config.CHANNEL_ID,
                        audio=media.file_id,
                        caption=caption_to_post,
                        parse_mode='Markdown'
                    )
                elif media.media_type == "voice":
                    await context.bot.send_voice(
                        chat_id=self.config.CHANNEL_ID,
                        voice=media.file_id,
                        caption=caption_to_post,
                        parse_mode='Markdown'
                    )
                elif media.media_type == "document":
                    await context.bot.send_document(
                        chat_id=self.config.CHANNEL_ID,
                        document=media.file_id,
                        caption=caption_to_post,
                        parse_mode='Markdown'
                    )
                elif media.media_type == "animation":
                    await context.bot.send_animation(
                        chat_id=self.config.CHANNEL_ID,
                        animation=media.file_id,
                        caption=caption_to_post,
                        parse_mode='Markdown'
                    )
                elif media.media_type == "sticker":
                    await context.bot.send_sticker(
                        chat_id=self.config.CHANNEL_ID,
                        sticker=media.file_id
                    )
                    
                await context.bot.send_message(
                    chat_id=media.user_id,
                    text="✅ پیام رسانه‌ای شما با موفقیت در کانال منتشر شد."
                )
                logger.info(f"Media {media_id} approved and posted to channel by admin {admin_id}.")

            except TelegramError as e:
                logger.error(f"Error posting approved media {media_id} to channel by admin {admin_id}: {e}")
                try:
                    await context.bot.send_message(
                        chat_id=media.user_id,
                        text="❌ متاسفانه در انتشار پیام رسانه‌ای شما به کانال خطایی رخ داد."
                    )
                except TelegramError as user_e:
                    logger.error(f"Failed to notify user {media.user_id} about media posting error: {user_e}")
                # Revert status if posting fails
                self.media_manager.update_media_status(media_id, None, None) 
                self.stats['media_approved'] -= 1
                self.stats['media_pending'] += 1 # Put it back to pending
                
        else:
            self.stats['media_rejected'] += 1
            self.stats['media_pending'] -= 1
            try:
                await context.bot.send_message(
                    chat_id=media.user_id,
                    text="❌ پیام رسانه‌ای شما توسط مدیر رد شد."
                )
                logger.info(f"Media {media_id} rejected by admin {admin_id}.")
            except TelegramError as e:
                logger.error(f"Error notifying user {media.user_id} about media rejection: {e}")

        # Edit admin's original message to reflect decision
        try:
            await query.edit_message_text(f"رسانه توسط شما **{action_text}** شد.\n"
                                          f"**از طرف:** {query.from_user.first_name} (ID: `{admin_id}`)",
                                          parse_mode='Markdown')
        except TelegramError as e:
            logger.error(f"Error editing admin message for media {media_id} decision: {e}")

        # Remove media from pending list after processing (regardless of outcome)
        self.media_manager.remove_processed_media(media_id)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a telegram message to notify the developer."""
        logger.error("Exception while handling an update:", exc_info=context.error)
        
        # traceback_text = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
        # update_str = update.to_dict() if isinstance(update, Update) else str(update)
        
        # error_message = (
        #     f"An exception was raised while handling an update:\n"
        #     f"<pre>update = {html.escape(json.dumps(update_str, indent=2))}"
        #     f"</pre>\n\n"
        #     f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        #     f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        #     f"<pre>{html.escape(traceback_text)}</pre>"
        # )
        
        # For simplicity, send a basic error message
        error_message_to_admin = f"🚨 **خطا در ربات!** 🚨\n\n`{context.error}`\n\nبرای جزئیات بیشتر لاگ‌ها را بررسی کنید."
        
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
                logger.error(f"Failed to send error reply to user {update.effective_user.id}: {e}")