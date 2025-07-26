"""
Telegram bot handlers for processing messages and commands
"""

import logging
import time
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
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

        if self.user_manager.is_user_banned(user.id):
            await update.message.reply_text("متاسفانه شما از استفاده از این ربات محروم شده‌اید.")
            logger.info(f"Banned user {user.id} tried to use /start.")
            return

        welcome_message = (
            f"سلام {user_profile.display_name} عزیز!\n\n"
            "به ربات مدیریت محتوا خوش آمدید. این ربات به شما کمک می‌کند تا محتوای خود را برای انتشار در کانال ارسال کنید.\n\n"
            "با استفاده از دکمه‌های زیر می‌توانید عملیات مورد نظر خود را انجام دهید:"
        )
        await self.send_main_menu(update.effective_chat.id, context, welcome_message)
        logger.info(f"User {user.id} ({user_profile.display_name}) started the bot.")

    async def send_main_menu(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE, message_text: str = "لطفاً یک گزینه را انتخاب کنید:"):
        """Sends the main menu keyboard to the user."""
        keyboard = [
            [InlineKeyboardButton("ارسال محتوا", callback_data="send_content")],
            [InlineKeyboardButton("تغییر نام نمایشی", callback_data="set_display_name")],
            [InlineKeyboardButton("راهنما", callback_data="help")],
            [InlineKeyboardButton("درباره ما", callback_data="about")]
        ]
        if self.config.is_admin(chat_id): # Only show admin button to admins
            keyboard.append([InlineKeyboardButton("پنل ادمین", callback_data="admin_panel")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=reply_markup
            )
            logger.info(f"Sent main menu to chat {chat_id}.")
        except TelegramError as e:
            logger.error(f"Failed to send main menu to chat {chat_id}: {e}")

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /menu command to show the main menu."""
        chat_id = update.effective_chat.id
        await self.send_main_menu(chat_id, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user_id = update.effective_user.id
        if self.user_manager.is_user_banned(user_id):
            await update.message.reply_text("متاسفانه شما از استفاده از این ربات محروم شده‌اید.")
            logger.info(f"Banned user {user_id} tried to use /help.")
            return

        help_message = (
            "راهنمای استفاده از ربات:\n\n"
            "✨ *ارسال محتوا*: محتوای متنی، عکس، ویدئو یا گیف خود را برای ما بفرستید تا پس از بررسی توسط ادمین، در کانال منتشر شود.\n"
            "✏️ *تغییر نام نمایشی*: با استفاده از این گزینه می‌توانید نامی که در کانال نمایش داده می‌شود را تغییر دهید.\n"
            "❓ *راهنما*: این پیام راهنما را نمایش می‌دهد.\n"
            "ℹ️ *درباره ما*: اطلاعاتی درباره سازنده و هدف ربات ارائه می‌دهد.\n\n"
            "⚠️ *توجه*: تمام محتوا قبل از انتشار توسط فیلتر محتوای نامناسب بررسی و سپس توسط ادمین تایید می‌شود. لطفاً از ارسال محتوای غیر اخلاقی یا توهین‌آمیز خودداری کنید."
        )
        if update.message:
            await update.message.reply_text(help_message, parse_mode='Markdown')
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(help_message, parse_mode='Markdown')
        logger.info(f"User {user_id} requested help.")

    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /about command"""
        user_id = update.effective_user.id
        if self.user_manager.is_user_banned(user_id):
            await update.message.reply_text("متاسفانه شما از استفاده از این ربات محروم شده‌اید.")
            logger.info(f"Banned user {user_id} tried to use /about.")
            return

        about_message = (
            "🤖 *درباره ربات مدیریت محتوا*\n\n"
            "این ربات با هدف تسهیل ارسال و مدیریت محتوا برای یک کانال تلگرامی توسعه یافته است.\n"
            "**توسعه‌دهنده**: [نام توسعه‌دهنده یا لینک گیت‌هاب](https://github.com/your-github-profile)\n"
            "**نسخه**: 1.0.0\n"
            "**تاریخ انتشار**: 2025-07-26\n\n"
            "امیدواریم این ربات برای شما مفید باشد!"
        )
        if update.message:
            await update.message.reply_text(about_message, parse_mode='Markdown', disable_web_page_preview=True)
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(about_message, parse_mode='Markdown', disable_web_page_preview=True)
        logger.info(f"User {user_id} requested about info.")

    async def set_name_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set_name command or callback to set display name"""
        user_id = update.effective_user.id
        if self.user_manager.is_user_banned(user_id):
            # Determine which message object to reply to
            if update.message:
                await update.message.reply_text("متاسفانه شما از استفاده از این ربات محروم شده‌اید.")
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("متاسفانه شما از استفاده از این ربات محروم شده‌اید.")
            logger.info(f"Banned user {user_id} tried to use /set_name.")
            return

        self.user_manager.set_user_setting_name_mode(user_id, True)

        # Correctly get the message object to reply to
        message_to_reply_to: Optional[Message] = None
        if update.message:
            message_to_reply_to = update.message
        elif update.callback_query and update.callback_query.message:
            message_to_reply_to = update.callback_query.message

        if message_to_reply_to:
            await message_to_reply_to.reply_text("لطفاً نام نمایشی جدید خود را ارسال کنید:")
            logger.info(f"User {user_id} entered name setting mode.")
        else:
            logger.warning(f"Could not find a message object to reply for user {user_id} in set_name_command.")


    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        user = update.effective_user
        if not user or not update.message:
            return

        user_id = user.id
        chat_id = update.effective_chat.id
        text = update.message.text
        logger.info(f"Received text message from {user_id} ({user.username}): '{text}'")

        if self.user_manager.is_user_banned(user_id):
            await update.message.reply_text("متاسفانه شما از استفاده از این ربات محروم شده‌اید.")
            logger.info(f"Banned user {user_id} sent a message: '{text}'")
            return

        self.stats["messages_processed"] += 1
        self.user_manager.increment_message_count(user_id) # Increment message count

        if self.user_manager.is_user_setting_name_mode(user_id):
            new_name = text.strip()
            if not new_name:
                await update.message.reply_text("نام نمایشی نمی‌تواند خالی باشد. لطفاً یک نام معتبر ارسال کنید:")
                return

            if len(new_name) > 50:
                await update.message.reply_text("نام نمایشی شما خیلی طولانی است. لطفاً نام کوتاه‌تری انتخاب کنید (حداکثر 50 کاراکتر).")
                return

            if self.user_manager.set_display_name(user_id, new_name):
                user_profile = self.user_manager.get_user_profile(user_id)
                await update.message.reply_text(f"نام نمایشی شما با موفقیت به '{user_profile.display_name}' تغییر یافت.")
                self.user_manager.set_user_setting_name_mode(user_id, False) # Exit name setting mode
                logger.info(f"User {user_id} changed display name to '{new_name}'.")
            else:
                await update.message.reply_text("این نام نمایشی قبلاً استفاده شده است. لطفاً نام دیگری انتخاب کنید.")
                logger.info(f"User {user_id} failed to change display name to '{new_name}' (name taken).")
            return

        # Regular message handling (profanity filter and media submission)
        if self.profanity_filter.contains_profanity(text):
            self.stats["messages_filtered"] += 1
            await update.message.reply_text(
                "پیام شما حاوی کلمات نامناسب است و قابل ارسال نیست. لطفاً پیام دیگری ارسال کنید."
            )
            logger.warning(f"Profanity detected from user {user_id}: '{text}'")
            return

        # If it's a direct message from user to bot, queue for approval
        if update.message.chat.type == "private":
            user_profile = self.user_manager.get_user_profile(user_id)
            username = user_profile.telegram_username if user_profile else user.username or "Unknown"

            media_id = self.media_manager.add_pending_media(
                user_id=user_id,
                username=username,
                message_id=update.message.message_id,
                media_type="text",
                file_id=None, # No file_id for text messages
                caption=text # Text content becomes the caption
            )

            await update.message.reply_text(
                "پیام متنی شما دریافت شد و برای بررسی به ادمین ارسال گردید. پس از تأیید در کانال منتشر خواهد شد."
            )
            logger.info(f"Text message from {user_id} queued for approval. Media ID: {media_id}")

            # Notify admin
            if self.config.ADMIN_USER_ID:
                await self.send_admin_approval_request(update, context, media_id, "متن")

    async def handle_media_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming media messages (photo, video, document etc.)"""
        user = update.effective_user
        if not user or not update.message:
            return

        user_id = user.id
        chat_id = update.effective_chat.id
        caption = update.message.caption or ""
        media_type = "unknown"
        file_id = None

        if self.user_manager.is_user_banned(user_id):
            await update.message.reply_text("متاسفانه شما از استفاده از این ربات محروم شده‌اید.")
            logger.info(f"Banned user {user_id} sent a media message.")
            return

        self.stats["messages_processed"] += 1
        self.user_manager.increment_message_count(user_id) # Increment message count

        if update.message.photo:
            media_type = "photo"
            file_id = update.message.photo[-1].file_id # Get the highest resolution photo
        elif update.message.video:
            media_type = "video"
            file_id = update.message.video.file_id
        elif update.message.animation: # This is for GIFs
            media_type = "animation"
            file_id = update.message.animation.file_id
        elif update.message.document: # General files, can be anything, incl. GIFs not classified as animation
            media_type = "document"
            file_id = update.message.document.file_id
        elif update.message.audio:
            media_type = "audio"
            file_id = update.message.audio.file_id
        elif update.message.voice:
            media_type = "voice"
            file_id = update.message.voice.file_id
        elif update.message.sticker:
            media_type = "sticker"
            file_id = update.message.sticker.file_id
        # Add more media types as needed

        if not file_id:
            await update.message.reply_text("نوع رسانه ارسالی شما پشتیبانی نمی‌شود یا فایل یافت نشد. لطفاً عکس، ویدئو یا گیف ارسال کنید.")
            logger.warning(f"Unsupported media type received from user {user_id}: {update.message}")
            return

        if self.profanity_filter.contains_profanity(caption):
            self.stats["messages_filtered"] += 1
            await update.message.reply_text(
                "کپشن شما حاوی کلمات نامناسب است و قابل ارسال نیست. لطفاً کپشن دیگری ارسال کنید."
            )
            logger.warning(f"Profanity detected in caption from user {user_id}: '{caption}'")
            return

        user_profile = self.user_manager.get_user_profile(user_id)
        username = user_profile.telegram_username if user_profile else user.username or "Unknown"

        media_id = self.media_manager.add_pending_media(
            user_id=user_id,
            username=username,
            message_id=update.message.message_id,
            media_type=media_type,
            file_id=file_id,
            caption=caption
        )

        await update.message.reply_text(
            f"محتوای ({media_type}) شما دریافت شد و برای بررسی به ادمین ارسال گردید. پس از تأیید در کانال منتشر خواهد شد."
        )
        logger.info(f"Media ({media_type}) from {user_id} queued for approval. Media ID: {media_id}")

        # Notify admin
        if self.config.ADMIN_USER_ID:
            await self.send_admin_approval_request(update, context, media_id, media_type)

    async def send_admin_approval_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, media_id: str, media_type: str):
        """Send a message to the admin with approval buttons."""
        if not self.config.ADMIN_USER_ID:
            logger.warning("ADMIN_USER_ID is not set. Cannot send approval request to admin.")
            return

        pending_media_item = self.media_manager.get_pending_media_by_id(media_id)
        if not pending_media_item:
            logger.error(f"Pending media item with ID {media_id} not found for admin request.")
            return

        # Forward the original message to the admin
        try:
            # For messages with media, forward the original message
            # For text messages, just send the text
            if pending_media_item.file_id:
                forwarded_message = await context.bot.forward_message(
                    chat_id=self.config.ADMIN_USER_ID,
                    from_chat_id=pending_media_item.user_id,
                    message_id=pending_media_item.message_id
                )
                original_message_link = forwarded_message.link if forwarded_message else "لینک پیام ناموجود"
            else:
                # For text-only messages, create a similar message
                # Or just send the caption as the content
                original_message_link = "پیام متنی (بدون فوروارد مستقیم)" # No direct link for new text message

            user_profile = self.user_manager.get_user_profile(pending_media_item.user_id)
            display_name = user_profile.display_name if user_profile else pending_media_item.username
            user_number = user_profile.user_number if user_profile else "N/A"

            approval_message_text = (
                f"✅ محتوای جدید برای تأیید:\n\n"
                f"📝 *نوع*: {media_type}\n"
                f"👤 *فرستنده*: {display_name} (ID: `{pending_media_item.user_id}`, شماره کاربر: {user_number})\n"
                f"🆔 *شناسه محتوا*: `{media_id}`\n"
            )
            if pending_media_item.caption:
                approval_message_text += f"💬 *کپشن/متن*: {pending_media_item.caption}\n"

            # Add link to original message if available and relevant
            if pending_media_item.file_id: # Only for media that can be forwarded
                approval_message_text += f"[مشاهده پیام اصلی]({original_message_link})\n"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ تأیید", callback_data=f"approve_{media_id}"),
                 InlineKeyboardButton("❌ رد", callback_data=f"reject_{media_id}")]
            ])

            await context.bot.send_message(
                chat_id=self.config.ADMIN_USER_ID,
                text=approval_message_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            logger.info(f"Approval request for media ID {media_id} sent to admin {self.config.ADMIN_USER_ID}.")

        except TelegramError as e:
            logger.error(f"Failed to send approval request to admin {self.config.ADMIN_USER_ID}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while sending admin approval request for media ID {media_id}: {e}", exc_info=True)


    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        if not query:
            logger.warning("Callback query is None.")
            return

        user_id = query.from_user.id
        chat_id = query.message.chat_id if query.message else query.from_user.id
        data = query.data
        logger.info(f"Callback query from user {user_id} in chat {chat_id}: {data}")

        await query.answer() # Acknowledge the query immediately

        if data == "send_content":
            if self.user_manager.is_user_banned(user_id):
                await query.message.reply_text("متاسفانه شما از استفاده از این ربات محروم شده‌اید.")
                logger.info(f"Banned user {user_id} tried to use 'send_content' button.")
                return
            await query.message.reply_text(
                "لطفاً محتوای (متن، عکس، ویدئو یا گیف) خود را ارسال کنید. می‌توانید کپشن هم بنویسید."
            )
            logger.info(f"User {user_id} chose 'send_content'.")
        elif data == "set_display_name":
            await self.set_name_command(update, context) # Re-use the command handler logic
            logger.info(f"User {user_id} chose 'set_display_name'.")
        elif data == "help":
            await self.help_command(update, context)
            logger.info(f"User {user_id} chose 'help'.")
        elif data == "about":
            await self.about_command(update, context)
            logger.info(f"User {user_id} chose 'about'.")
        elif data == "admin_panel":
            if self.config.is_admin(user_id):
                await self.send_admin_menu(chat_id, context)
                logger.info(f"Admin {user_id} accessed admin panel.")
            else:
                await query.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
                logger.warning(f"Non-admin user {user_id} tried to access admin panel.")
        elif data.startswith(("approve_", "reject_")):
            if not self.config.is_admin(user_id):
                await query.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
                logger.warning(f"Non-admin user {user_id} tried to approve/reject media.")
                return

            media_id = data.split("_")[1]
            action = data.split("_")[0] # 'approve' or 'reject'

            # Get the pending media item
            pending_media_item = self.media_manager.get_pending_media_by_id(media_id)

            if not pending_media_item:
                await query.message.edit_text("این محتوا قبلاً پردازش شده یا یافت نشد.")
                logger.warning(f"Admin {user_id} tried to process non-existent media {media_id}.")
                return

            # Check if it's already processed to prevent double processing
            if pending_media_item.approved is not None:
                status = "تأیید" if pending_media_item.approved else "رد"
                await query.message.edit_text(f"این محتوا قبلاً توسط ادمین {pending_media_item.admin_id or ''} {status} شده است.")
                logger.info(f"Admin {user_id} tried to re-process media {media_id} which was already {status}.")
                return

            original_sender_id = pending_media_item.user_id
            user_profile = self.user_manager.get_user_profile(original_sender_id)
            sender_display_name = user_profile.display_name if user_profile else pending_media_item.username

            if action == "approve":
                # Send the media to the channel
                try:
                    if pending_media_item.media_type == "text":
                        # For text messages, just send the caption as text
                        sent_message = await context.bot.send_message(
                            chat_id=self.config.CHANNEL_ID,
                            text=f"پیام از {sender_display_name}:\n\n{pending_media_item.caption}",
                            parse_mode='Markdown'
                        )
                    elif pending_media_item.media_type == "photo":
                        sent_message = await context.bot.send_photo(
                            chat_id=self.config.CHANNEL_ID,
                            photo=pending_media_item.file_id,
                            caption=f"عکس از {sender_display_name}:\n\n{pending_media_item.caption}",
                            parse_mode='Markdown'
                        )
                    elif pending_media_item.media_type == "video":
                        sent_message = await context.bot.send_video(
                            chat_id=self.config.CHANNEL_ID,
                            video=pending_media_item.file_id,
                            caption=f"ویدئو از {sender_display_name}:\n\n{pending_media_item.caption}",
                            parse_mode='Markdown'
                        )
                    elif pending_media_item.media_type == "animation":
                        sent_message = await context.bot.send_animation(
                            chat_id=self.config.CHANNEL_ID,
                            animation=pending_media_item.file_id,
                            caption=f"گیف از {sender_display_name}:\n\n{pending_media_item.caption}",
                            parse_mode='Markdown'
                        )
                    elif pending_media_item.media_type == "document":
                        sent_message = await context.bot.send_document(
                            chat_id=self.config.CHANNEL_ID,
                            document=pending_media_item.file_id,
                            caption=f"فایل از {sender_display_name}:\n\n{pending_media_item.caption}",
                            parse_mode='Markdown'
                        )
                    elif pending_media_item.media_type == "audio":
                        sent_message = await context.bot.send_audio(
                            chat_id=self.config.CHANNEL_ID,
                            audio=pending_media_item.file_id,
                            caption=f"فایل صوتی از {sender_display_name}:\n\n{pending_media_item.caption}",
                            parse_mode='Markdown'
                        )
                    elif pending_media_item.media_type == "voice":
                        sent_message = await context.bot.send_voice(
                            chat_id=self.config.CHANNEL_ID,
                            voice=pending_media_item.file_id,
                            caption=f"پیام صوتی از {sender_display_name}:\n\n{pending_media_item.caption}",
                            parse_mode='Markdown'
                        )
                    elif pending_media_item.media_type == "sticker":
                        sent_message = await context.bot.send_sticker(
                            chat_id=self.config.CHANNEL_ID,
                            sticker=pending_media_item.file_id,
                        )
                    else:
                        await query.message.edit_text(f"خطا: نوع رسانه '{pending_media_item.media_type}' پشتیبانی نمی‌شود.")
                        logger.error(f"Unsupported media type for sending: {pending_media_item.media_type} for media ID {media_id}")
                        return

                    self.media_manager.approve_media(media_id, user_id)
                    self.stats["messages_posted"] += 1
                    await query.message.edit_text(f"✅ محتوا تأیید و در کانال منتشر شد! (ID: `{media_id}`)")
                    logger.info(f"Media {media_id} approved and posted by admin {user_id}.")

                    # Notify original sender
                    try:
                        await context.bot.send_message(
                            chat_id=original_sender_id,
                            text="محتوای ارسالی شما با موفقیت در کانال منتشر شد! ✅"
                        )
                    except TelegramError as e:
                        logger.warning(f"Could not notify user {original_sender_id} about approved media {media_id}: {e}")

                except TelegramError as e:
                    await query.message.edit_text(f"❌ خطا در انتشار محتوا به کانال: {e}")
                    logger.error(f"Failed to post media {media_id} to channel: {e}")
                except Exception as e:
                    await query.message.edit_text(f"❌ خطای ناشناخته در انتشار محتوا: {e}")
                    logger.error(f"Unexpected error when posting media {media_id}: {e}", exc_info=True)


            elif action == "reject":
                self.media_manager.reject_media(media_id, user_id)
                self.stats["media_rejected"] += 1
                await query.message.edit_text(f"❌ محتوا رد شد. (ID: `{media_id}`)")
                logger.info(f"Media {media_id} rejected by admin {user_id}.")

                # Notify original sender
                try:
                    await context.bot.send_message(
                        chat_id=original_sender_id,
                        text="متاسفانه محتوای ارسالی شما رد شد. ❌"
                    )
                except TelegramError as e:
                    logger.warning(f"Could not notify user {original_sender_id} about rejected media {media_id}: {e}")

        # Admin Menu Callbacks
        elif data == "admin_stats":
            await self.admin_stats_command(update, context)
        elif data == "admin_list_pending":
            await self.admin_list_pending_command(update, context)
        elif data == "admin_ban_user":
            await self.admin_ban_user_command(update, context)
        elif data == "admin_unban_user":
            await self.admin_unban_user_command(update, context)
        elif data == "admin_return_to_main":
            await self.send_main_menu(chat_id, context, "به منوی اصلی بازگشتید:")
            logger.info(f"Admin {user_id} returned to main menu.")
        elif data == "admin_purge_old_pending":
            if self.config.is_admin(user_id):
                deleted_count = self.media_manager.purge_old_pending_media()
                await query.message.edit_text(f"✅ {deleted_count} محتوای در انتظار قدیمی پاک شد.")
                logger.info(f"Admin {user_id} purged {deleted_count} old pending media.")
            else:
                await query.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            await self.send_admin_menu(chat_id, context) # Show admin menu again
        else:
            logger.warning(f"Unhandled callback query data: {data}")
            await query.message.reply_text("دستور ناشناخته.")


    async def send_admin_menu(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE, message_text: str = "پنل ادمین:") -> None:
        """Sends the admin menu keyboard."""
        keyboard = [
            [InlineKeyboardButton("آمار ربات", callback_data="admin_stats")],
            [InlineKeyboardButton("لیست محتواهای در انتظار", callback_data="admin_list_pending")],
            [
                InlineKeyboardButton("مسدود کردن کاربر", callback_data="admin_ban_user"),
                InlineKeyboardButton("رفع مسدودیت کاربر", callback_data="admin_unban_user")
            ],
            [InlineKeyboardButton("پاکسازی محتواهای قدیمی", callback_data="admin_purge_old_pending")],
            [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="admin_return_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=reply_markup
            )
            logger.info(f"Sent admin menu to chat {chat_id}.")
        except TelegramError as e:
            logger.error(f"Failed to send admin menu to chat {chat_id}: {e}")

    # New method to handle /admin_menu command
    async def admin_menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin_menu command to show the admin menu."""
        user_id = update.effective_user.id
        if not self.config.is_admin(user_id):
            if update.message:
                await update.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            logger.warning(f"Non-admin user {user_id} tried to access /admin_menu.")
            return

        chat_id = update.effective_chat.id
        await self.send_admin_menu(chat_id, context)
        logger.info(f"Admin {user_id} used /admin_menu command.")


    async def admin_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot statistics to admin"""
        user_id = update.effective_user.id
        if not self.config.is_admin(user_id):
            if update.message:
                await update.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            logger.warning(f"Non-admin user {user_id} tried to access /admin_stats.")
            return

        user_stats = self.user_manager.get_user_stats()
        media_stats = self.media_manager.get_media_stats()

        stats_message = (
            "📊 *آمار ربات:*\n\n"
            "*آمار کلی پیام‌ها و محتواها:*\n"
            f"  • پیام‌های پردازش شده: {self.stats['messages_processed']}\n"
            f"  • پیام‌های فیلتر شده (نامناسب): {self.stats['messages_filtered']}\n"
            f"  • محتواهای ارسال شده در کانال: {self.stats['messages_posted']}\n"
            f"  • محتواهای در انتظار (تایید/رد نشده): {media_stats['pending_count']}\n"
            f"  • محتواهای تایید شده: {self.stats['media_approved']}\n"
            f"  • محتواهای رد شده: {self.stats['media_rejected']}\n\n"
            "*آمار کاربران:*\n"
            f"  • کل کاربران: {user_stats['total_users']}\n"
            f"  • کاربران با نام نمایشی سفارشی: {user_stats['custom_names']}\n"
            f"  • کاربران با نام نمایشی پیش‌فرض: {user_stats['default_names']}\n"
            f"  • کل پیام‌های ارسالی کاربران: {user_stats['total_messages']}\n\n"
            "🗓️ آخرین پاکسازی محتواهای قدیمی: (هر 24 ساعت یکبار به صورت خودکار انجام می‌شود)"
        )
        # Determine which message object to reply to
        if update.message:
            await update.message.reply_text(stats_message, parse_mode='Markdown')
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.edit_text(stats_message, parse_mode='Markdown', reply_markup=self.get_back_to_admin_menu_markup())
        logger.info(f"Admin {user_id} requested stats.")

    def get_back_to_admin_menu_markup(self):
        """Returns an inline keyboard markup to go back to admin menu."""
        keyboard = [[InlineKeyboardButton("بازگشت به پنل ادمین", callback_data="admin_panel")]]
        return InlineKeyboardMarkup(keyboard)

    async def admin_list_pending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List pending media items to admin"""
        user_id = update.effective_user.id
        if not self.config.is_admin(user_id):
            if update.message:
                await update.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            logger.warning(f"Non-admin user {user_id} tried to access /admin_list_pending.")
            return

        pending_items = self.media_manager.get_pending_media()
        if not pending_items:
            message_text = "هیچ محتوای در انتظاری وجود ندارد."
        else:
            message_text = "📥 *محتواهای در انتظار بررسی:*\n\n"
            for item in pending_items:
                user_profile = self.user_manager.get_user_profile(item.user_id)
                display_name = user_profile.display_name if user_profile else item.username
                message_text += (
                    f"▪️ *نوع*: {item.media_type}\n"
                    f"  *فرستنده*: {display_name} (ID: `{item.user_id}`)\n"
                    f"  *شناسه*: `{item.id}`\n"
                    f"  *کپشن*: {item.caption[:50]}...\n\n" # Show first 50 chars of caption
                )
        # Determine which message object to reply to
        if update.message:
            await update.message.reply_text(message_text, parse_mode='Markdown')
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.edit_text(message_text, parse_mode='Markdown', reply_markup=self.get_back_to_admin_menu_markup())
        logger.info(f"Admin {user_id} requested pending media list.")


    async def admin_ban_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to ban a user"""
        user_id = update.effective_user.id
        if not self.config.is_admin(user_id):
            if update.message:
                await update.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            logger.warning(f"Non-admin user {user_id} tried to access /admin_ban_user.")
            return

        # Prompt admin for user ID to ban
        context.user_data["awaiting_ban_user_id"] = True
        message_text = "لطفاً Telegram User ID کاربری که می‌خواهید مسدود کنید را ارسال کنید."

        if update.message:
            await update.message.reply_text(message_text)
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.edit_text(message_text, reply_markup=self.get_back_to_admin_menu_markup())
        logger.info(f"Admin {user_id} initiated user banning process.")

    async def admin_unban_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to unban a user"""
        user_id = update.effective_user.id
        if not self.config.is_admin(user_id):
            if update.message:
                await update.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            logger.warning(f"Non-admin user {user_id} tried to access /admin_unban_user.")
            return

        # Prompt admin for user ID to unban
        context.user_data["awaiting_unban_user_id"] = True
        message_text = "لطفاً Telegram User ID کاربری که می‌خواهید رفع مسدودیت کنید را ارسال کنید."

        if update.message:
            await update.message.reply_text(message_text)
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.edit_text(message_text, reply_markup=self.get_back_to_admin_menu_markup())
        logger.info(f"Admin {user_id} initiated user unbanning process.")

    async def admin_handle_ban_unban_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles input for banning/unbanning users."""
        admin_id = update.effective_user.id
        if not self.config.is_admin(admin_id):
            await update.message.reply_text("شما اجازه دسترسی به این بخش را ندارید.")
            logger.warning(f"Non-admin user {admin_id} tried to input ban/unban ID.")
            return

        if not update.message or not update.message.text:
            await update.message.reply_text("لطفاً یک عدد معتبر برای User ID ارسال کنید.")
            return

        try:
            target_user_id = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text("شناسه کاربری نامعتبر. لطفاً یک عدد صحیح وارد کنید.")
            return

        if context.user_data.get("awaiting_ban_user_id"):
            self.user_manager.ban_user(target_user_id)
            await update.message.reply_text(f"کاربر با شناسه `{target_user_id}` مسدود شد.")
            del context.user_data["awaiting_ban_user_id"]
            logger.info(f"Admin {admin_id} banned user {target_user_id}.")
            await self.send_admin_menu(admin_id, context) # Return to admin menu
        elif context.user_data.get("awaiting_unban_user_id"):
            self.user_manager.unban_user(target_user_id)
            await update.message.reply_text(f"کاربر با شناسه `{target_user_id}` رفع مسدودیت شد.")
            del context.user_data["awaiting_unban_user_id"]
            logger.info(f"Admin {admin_id} unbanned user {target_user_id}.")
            await self.send_admin_menu(admin_id, context) # Return to admin menu
        else:
            # If not awaiting ban/unban, just process as regular text message
            # This case might mean admin sent a number not related to ban/unban, so route to handle_text_message
            await self.handle_text_message(update, context) # Reroute to normal text handling
            logger.info(f"Admin {admin_id} sent a number that was not for ban/unban: {target_user_id}. Handled as normal text.")

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancels any ongoing user action, like setting name or awaiting ban/unban ID."""
        user_id = update.effective_user.id

        if self.user_manager.is_user_setting_name_mode(user_id):
            self.user_manager.set_user_setting_name_mode(user_id, False)
            await update.message.reply_text("عملیات تغییر نام نمایشی لغو شد.")
            logger.info(f"User {user_id} cancelled name setting mode.")
        elif context.user_data.get("awaiting_ban_user_id"):
            del context.user_data["awaiting_ban_user_id"]
            await update.message.reply_text("عملیات مسدود کردن کاربر لغو شد.")
            logger.info(f"Admin {user_id} cancelled user banning process.")
            if self.config.is_admin(user_id):
                await self.send_admin_menu(user_id, context)
        elif context.user_data.get("awaiting_unban_user_id"):
            del context.user_data["awaiting_unban_user_id"]
            await update.message.reply_text("عملیات رفع مسدودیت کاربر لغو شد.")
            logger.info(f"Admin {user_id} cancelled user unbanning process.")
            if self.config.is_admin(user_id):
                await self.send_admin_menu(user_id, context)
        else:
            await update.message.reply_text("هیچ عملیاتی برای لغو وجود ندارد.")
            logger.info(f"User {user_id} tried to cancel, but no pending operation.")

        # Ensure the menu is shown after cancellation if it's a command
        if update.message and update.message.chat.type == "private":
            await self.send_main_menu(update.effective_chat.id, context, "عملیات لغو شد. لطفاً یک گزینه را انتخاب کنید:")


    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a message to the admin."""
        logger.exception("Exception while handling an update:")
        # original_error_message = str(context.error)

        # Build error message for admin
        # traceback_text = ''.join(traceback.format_exception(type(context.error), context.error, context.error.__traceback__))
        # update_str = update.to_dict() if isinstance(update, Update) else str(update)
        # error_message_to_admin = (
        #     f"🚨 *خطا در ربات!* 🚨\\n\\n"
        #     f"An exception was raised while handling an update:\\n"
        #     f"<pre>update = {html.escape(json.dumps(update_str, indent=2))}</pre>\\n\\n"
        #     f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\\n\\n"
        #     f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\\n\\n"
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
                    "متاسفانه خطایی در پردازش درخواست شما رخ داد. لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
                )
            except TelegramError as e:
                logger.error(f"Failed to send error message to user {update.effective_user.id}: {e}")