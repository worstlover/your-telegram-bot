import logging
import time
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config import Config
from profanity_filter import ProfanityFilter
from media_manager import MediaManager, PendingMedia
from user_manager import UserManager, UserProfile

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
    
    # Helper to create the 'View Channel' keyboard
    def _get_view_channel_keyboard(self) -> InlineKeyboardMarkup:
        channel_url = f"https://t.me/{self.config.CHANNEL_ID.lstrip('@')}"
        keyboard = [[InlineKeyboardButton("مشاهده کانال", url=channel_url)]]
        return InlineKeyboardMarkup(keyboard)

    # Helper to create the main menu keyboard
    def _get_main_menu_keyboard(self, is_admin: bool = False) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("ارسال پیام جدید", callback_data="send_new_message")], # This is more informational, implies just type
            [InlineKeyboardButton("تنظیم نام نمایشی", callback_data="set_display_name_from_menu")],
            [InlineKeyboardButton("مشاهده کانال", url=f"https://t.me/{self.config.CHANNEL_ID.lstrip('@')}")]
        ]
        if is_admin:
            keyboard.append([InlineKeyboardButton("آمار (ادمین)", callback_data="show_admin_stats_from_menu")])
        keyboard.append([InlineKeyboardButton("راهنما", callback_data="show_help_from_menu")])
        
        return InlineKeyboardMarkup(keyboard)

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str = "لطفاً یک گزینه را انتخاب کنید:"):
        """Display the main menu to the user."""
        user = update.effective_user
        if not user:
            return

        is_admin = self.config.is_admin(user.id)
        reply_markup = self._get_main_menu_keyboard(is_admin)

        if update.message:
            await update.message.reply_text(message_text, reply_markup=reply_markup)
        elif update.callback_query:
            # Edit the original message that triggered the callback to show the menu
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
        logger.info(f"User {user.id} opened main menu.")
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        if not user:
            return
        
        # Register or get user profile
        user_profile = self.user_manager.register_user(user.id, user.username or user.first_name or "Unknown")
        
        welcome_message = f"""
🤖 **ربات انتشار ناشناس**

سلام {user.first_name or 'کاربر'}! به ربات انتشار ناشناس خوش آمدید.

**نام نمایشی شما:** `{user_profile.display_name}`

**امکانات:**
📝 **پیام های متنی:** با نام نمایشی شما در کانال منتشر می‌شود
📸 **رسانه ها:** بعد از تایید ادمین با نام نمایشی شما منتشر می‌شود

**حریم خصوصی:**
🔒 فقط نام نمایشی شما در کانال نمایش داده می‌شود
📝 اطلاعات شخصی شما ثبت یا ذخیره نمی‌شود
⚡ پیام‌های متنی بلافاصله در کانال درج می‌شوند

**نام نمایشی:**
• شما می‌توانید نام نمایشی دلخواه انتخاب کنید
• نام نمایشی بعد از تنظیم قابل تغییر نیست
• اگر نام انتخاب نکنید، شماره کاربری خودکار داده می‌شود

**قوانین:**
• از کلمات نامناسب خودداری کنید
• محتوای ارسالی باید مناسب و قابل انتشار باشد

برای کمک از /help استفاده کنید.
        """
        
        if update.message:
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            await self.show_main_menu(update, context, "لطفاً یک گزینه را انتخاب کنید:") # Show main menu after welcome
        logger.info(f"User {user.id} ({user.username or user.first_name}) started the bot and saw main menu.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
📖 **راهنمای استفاده**

**ارسال پیام متنی:**
• پیام خود را بنویسید و ارسال کنید
• ربات آن را بررسی و بدون نام شما در کانال منتشر می‌کند
• پیام‌های حاوی کلمات نامناسب فیلتر می‌شود

**ارسال رسانه:**
• تصاویر، ویدیوها و فایل‌هایتان را ارسال کنید
• این موارد برای تایید نزد ادمین ارسال می‌شود
• بعد از تأیید بدون نام شما در کانال منتشر خواهد شد

**حریم خصوصی:**
🔒 تمام پیام‌ها کاملاً ناشناس منتشر می‌شوند
📝 هیچ اطلاعاتی از شما ثبت نمی‌شود
⚡ پیام‌های متنی فوری منتشر می‌شوند

**دستورات:**
• /start: شروع و اطلاعات اولیه
• /menu: نمایش منوی اصلی
• /help: نمایش این راهنما
• /set_name: تنظیم نام نمایشی
• /my_name: نمایش نام نمایشی شما

**قوانین عمومی:**
• از ارسال محتوای غیرقانونی، توهین‌آمیز یا نامناسب خودداری کنید.
• احترام به سایر کاربران را رعایت کنید.
• در صورت نقض قوانین، دسترسی شما ممکن است محدود شود.
"""
        if update.message:
            await update.message.reply_text(help_message, parse_mode='Markdown', reply_markup=self._get_main_menu_keyboard(self.config.is_admin(update.effective_user.id)))
        elif update.callback_query:
            await update.callback_query.edit_message_text(help_message, parse_mode='Markdown', reply_markup=self._get_main_menu_keyboard(self.config.is_admin(update.effective_user.id)))
        logger.info(f"User {update.effective_user.id} requested help")

    async def set_name_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set_name command and callback for setting display name"""
        user = update.effective_user
        if not user:
            return

        user_profile = self.user_manager.get_user_profile(user.id)
        if user_profile and not user_profile.display_name.startswith("کاربر شماره"):
            if update.message:
                await update.message.reply_text(
                    f"نام نمایشی شما از قبل تنظیم شده است: `{user_profile.display_name}`\n"
                    "نام نمایشی بعد از تنظیم قابل تغییر نیست.",
                    parse_mode='Markdown',
                    reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
                )
            elif update.callback_query:
                await update.callback_query.edit_message_text(
                    f"نام نمایشی شما از قبل تنظیم شده است: `{user_profile.display_name}`\n"
                    "نام نمایشی بعد از تنظیم قابل تغییر نیست.",
                    parse_mode='Markdown',
                    reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
                )
            logger.info(f"User {user.id} tried to set name again, but already has one.")
            return

        self.user_manager.set_user_setting_name_mode(user.id, True)
        
        keyboard = [[InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text(
                "لطفاً نام نمایشی مورد نظر خود را ارسال کنید.\n"
                "نام انتخابی شما در کانال نمایش داده خواهد شد و بعداً قابل تغییر نیست.",
                reply_markup=reply_markup
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                "لطفاً نام نمایشی مورد نظر خود را ارسال کنید.\n"
                "نام انتخابی شما در کانال نمایش داده خواهد شد و بعداً قابل تغییر نیست.",
                reply_markup=reply_markup
            )
        logger.info(f"User {user.id} entered name setting mode.")

    async def my_name_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /my_name command"""
        user = update.effective_user
        if not user:
            return

        user_profile = self.user_manager.get_user_profile(user.id)
        if user_profile:
            await update.message.reply_text(
                f"نام نمایشی شما: `{user_profile.display_name}`",
                parse_mode='Markdown',
                reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
            )
        else:
            await update.message.reply_text("شما هنوز در ربات ثبت‌نام نکرده‌اید. لطفا از /start استفاده کنید.", reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id)))
        logger.info(f"User {user.id} requested their display name.")

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        user = update.effective_user
        if not user or not update.message or not update.message.text:
            return

        user_profile = self.user_manager.get_user_profile(user.id)
        if not user_profile:
            # If user somehow sends message before /start, register them
            user_profile = self.user_manager.register_user(user.id, user.username or user.first_name or "Unknown")
            await update.message.reply_text(
                "شما ثبت‌نام شدید! لطفا پیام خود را دوباره ارسال کنید.",
                parse_mode='Markdown',
                reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
            )
            logger.info(f"Registered new user {user.id} from text message.")
            return

        # Check if user is in name setting mode
        if self.user_manager.is_user_setting_name(user.id):
            display_name = update.message.text.strip()
            if len(display_name) > 30:
                await update.message.reply_text("نام نمایشی شما خیلی طولانی است. لطفاً یک نام حداکثر ۳۰ کاراکتری انتخاب کنید.", reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id)))
                logger.info(f"User {user.id} tried to set too long display name.")
                return
            if len(display_name) < 3:
                await update.message.reply_text("نام نمایشی شما خیلی کوتاه است. لطفاً یک نام حداقل ۳ کاراکتری انتخاب کنید.", reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id)))
                logger.info(f"User {user.id} tried to set too short display name.")
                return
            
            # Check for profanity in the chosen display name
            has_profanity, _ = self.profanity_filter.contains_profanity(display_name)
            if has_profanity:
                await update.message.reply_text("نام نمایشی انتخابی شما حاوی کلمات نامناسب است. لطفاً نام دیگری انتخاب کنید.", reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id)))
                logger.info(f"User {user.id} tried to set profanity display name.")
                return

            success = self.user_manager.set_display_name(user.id, display_name)
            if success:
                self.user_manager.set_user_setting_name_mode(user.id, False)
                await update.message.reply_text(
                    f"نام نمایشی شما با موفقیت به `{display_name}` تغییر یافت.",
                    parse_mode='Markdown',
                    reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
                )
                logger.info(f"User {user.id} successfully set display name to '{display_name}'.")
            else:
                await update.message.reply_text(
                    "این نام نمایشی قبلاً توسط شخص دیگری انتخاب شده است. لطفاً نام دیگری انتخاب کنید.",
                    reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
                )
                logger.info(f"User {user.id} failed to set display name '{display_name}' (already taken).")
            return

        text = update.message.text
        self.stats["messages_processed"] += 1

        # Profanity filter
        has_profanity, found_words = self.profanity_filter.contains_profanity(text)

        if has_profanity:
            self.stats["messages_filtered"] += 1
            if self.config.STRICT_FILTERING:
                await update.message.reply_text(
                    f"پیام شما حاوی کلمات نامناسب ({', '.join(found_words)}) است و منتشر نخواهد شد. لطفاً قوانین را رعایت کنید.",
                    reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
                )
                logger.info(f"Blocked profanity message from {user.id}: '{text}'")
                return
            else:
                filtered_text = self.profanity_filter.censor_profanity(text)
                logger.info(f"Censored profanity message from {user.id}: original='{text}', filtered='{filtered_text}'")
                text = filtered_text

        # Prepare message for channel
        display_name = user_profile.display_name
        message_to_post = f"**{display_name}**: {text}"

        try:
            if len(message_to_post) > self.config.MAX_MESSAGE_LENGTH:
                await update.message.reply_text(
                    f"پیام شما خیلی طولانی است ({len(message_to_post)} کاراکتر). حداکثر طول پیام مجاز {self.config.MAX_MESSAGE_LENGTH} کاراکتر است. لطفاً پیام کوتاه‌تری ارسال کنید.",
                    reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
                )
                logger.warning(f"Message from {user.id} too long: {len(message_to_post)} chars.")
                return

            await context.bot.send_message(
                chat_id=self.config.CHANNEL_ID,
                text=message_to_post,
                parse_mode='Markdown'
            )
            self.stats["messages_posted"] += 1
            self.user_manager.increment_message_count(user.id)
            await update.message.reply_text(
                "پیام شما با موفقیت در کانال منتشر شد.",
                reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
            )
            logger.info(f"Text message from {user.id} posted successfully to channel.")
        except TelegramError as e:
            logger.error(f"Error posting message to channel: {e}")
            await update.message.reply_text(
                "خطایی در ارسال پیام به کانال رخ داد. لطفاً بعداً امتحان کنید.",
                reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            await update.message.reply_text(
                "خطایی نامشخص رخ داد. لطفاً بعداً امتحان کنید.",
                reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
            )

    async def handle_media_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming media messages (photo, video, audio, voice, document, animation, sticker)"""
        user = update.effective_user
        if not user or not update.message:
            return

        user_profile = self.user_manager.get_user_profile(user.id)
        if not user_profile:
            await update.message.reply_text(
                "شما هنوز در ربات ثبت‌نام نکرده‌اید. لطفا از /start استفاده کنید.",
                reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
            )
            logger.info(f"Blocked media from unregistered user {user.id}.")
            return

        media_id = None
        media_type = None
        caption = update.message.caption or ""

        if update.message.photo:
            media_id = update.message.photo[-1].file_id # Get the highest resolution photo
            media_type = "photo"
        elif update.message.video:
            media_id = update.message.video.file_id
            media_type = "video"
        elif update.message.audio:
            media_id = update.message.audio.file_id
            media_type = "audio"
        elif update.message.voice:
            media_id = update.message.voice.file_id
            media_type = "voice"
        elif update.message.document:
            media_id = update.message.document.file_id
            media_type = "document"
        elif update.message.animation:
            media_id = update.message.animation.file_id
            media_type = "animation"
        elif update.message.sticker:
            media_id = update.message.sticker.file_id
            media_type = "sticker"
        else:
            await update.message.reply_text(
                "نوع فایل ارسالی پشتیبانی نمی‌شود. لطفاً عکس، ویدئو، صدا، ویس، سند، گیف یا استیکر ارسال کنید.",
                reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
            )
            logger.warning(f"Unsupported media type received from {user.id}.")
            return

        if media_id:
            # Check for profanity in caption
            has_profanity, found_words = self.profanity_filter.contains_profanity(caption)
            if has_profanity:
                if self.config.STRICT_FILTERING:
                    await update.message.reply_text(
                        f"کپشن شما حاوی کلمات نامناسب ({', '.join(found_words)}) است. لطفاً کپشن مناسبی بنویسید.",
                        reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
                    )
                    logger.info(f"Blocked media with profanity caption from {user.id}.")
                    return
                else:
                    caption = self.profanity_filter.censor_profanity(caption)
                    logger.info(f"Censored media caption from {user.id}.")

            if self.media_manager.get_pending_media_count() >= self.config.MAX_PENDING_MEDIA:
                await update.message.reply_text(
                    "صف تأیید مدیا پر است. لطفاً بعداً دوباره امتحان کنید.",
                    reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
                )
                logger.warning(f"Media queue full for user {user.id}.")
                return

            # Add media to pending queue
            new_media = PendingMedia(
                id=str(int(time.time() * 1000)), # Unique ID
                user_id=user.id,
                username=user_profile.telegram_username,
                message_id=update.message.message_id,
                media_type=media_type,
                file_id=media_id,
                caption=caption,
                timestamp=time.time()
            )
            self.media_manager.add_pending_media(new_media)
            self.stats["media_pending"] += 1

            await update.message.reply_text(
                "رسانه شما برای تأیید توسط ادمین ارسال شد. پس از تأیید در کانال منتشر خواهد شد.",
                reply_markup=self._get_main_menu_keyboard(self.config.is_admin(user.id))
            )
            logger.info(f"Media from {user.id} ({media_type}) added to pending queue.")

            # Notify admin
            await self._send_media_for_approval(new_media, context)
        
    async def _send_media_for_approval(self, media: PendingMedia, context: ContextTypes.DEFAULT_TYPE):
        """Send media to admin for approval with inline keyboard"""
        try:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ تأیید", callback_data=f"approve_media_{media.id}"),
                 InlineKeyboardButton("❌ رد", callback_data=f"reject_media_{media.id}")]
            ])

            user_profile = self.user_manager.get_user_profile(media.user_id)
            display_name = user_profile.display_name if user_profile else f"کاربر ناشناس ({media.user_id})"

            approval_text = (
                f"**مدیا جدید برای تأیید:**\n\n"
                f"**ارسال کننده:** `{display_name}`\n"
                f"**نوع:** `{media.media_type}`\n"
                f"**کپشن:** `{media.caption or 'ندارد'}`\n"
                f"**ID مدیا:** `{media.id}`"
            )

            # Send the media itself
            if media.media_type == "photo":
                await context.bot.send_photo(
                    chat_id=self.config.ADMIN_USER_ID,
                    photo=media.file_id,
                    caption=approval_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            elif media.media_type == "video":
                await context.bot.send_video(
                    chat_id=self.config.ADMIN_USER_ID,
                    video=media.file_id,
                    caption=approval_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            elif media.media_type == "audio":
                await context.bot.send_audio(
                    chat_id=self.config.ADMIN_USER_ID,
                    audio=media.file_id
                )
            elif media.media_type == "voice":
                await context.bot.send_voice(
                    chat_id=self.config.ADMIN_USER_ID,
                    voice=media.file_id
                )
            elif media.media_type == "document":
                await context.bot.send_document(
                    chat_id=self.config.ADMIN_USER_ID,
                    document=media.file_id
                )
            elif media.media_type == "animation":
                await context.bot.send_animation(
                    chat_id=self.config.ADMIN_USER_ID,
                    animation=media.file_id
                )
            elif media.media_type == "sticker":
                await context.bot.send_sticker(
                    chat_id=self.config.ADMIN_USER_ID,
                    sticker=media.file_id
                )
            
            # Send approval message
            # If media type sends caption directly, no need for separate message
            if media.media_type not in ["photo", "video"]: # For media types that don't display caption with file
                 await context.bot.send_message(
                    chat_id=self.config.ADMIN_USER_ID,
                    text=approval_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )

            logger.info(f"Sent media {media.id} to admin for approval")
            
        except TelegramError as e:
            logger.error(f"Error sending media for approval: {e}")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer() # Acknowledge the query

        data = query.data

        # Handle main menu callbacks
        if data == "main_menu":
            await self.show_main_menu(update, context)
            return
        elif data == "send_new_message":
            await query.edit_message_text("لطفاً پیام متنی یا رسانه خود را ارسال کنید.")
            return
        elif data == "set_display_name_from_menu":
            await self.set_name_command(update, context) # Call the command handler for setting name
            return
        elif data == "show_help_from_menu":
            await self.help_command(update, context) # Call the command handler for help
            return
        elif data == "show_admin_stats_from_menu":
            if not self.config.is_admin(user_id):
                await query.edit_message_text("شما اجازه دسترسی به این عملکرد را ندارید.")
                logger.warning(f"Non-admin user {user_id} tried to access admin stats from menu.")
                return
            await self.admin_stats_command(update, context) # Call the command handler for admin stats
            return

        # Original admin approval logic
        if not self.config.is_admin(user_id):
            await query.edit_message_text("شما اجازه دسترسی به این عملکرد را ندارید.")
            logger.warning(f"Non-admin user {user_id} tried to use admin button.")
            return

        if data.startswith("approve_media_"):
            media_id = data.replace("approve_media_", "")
            media = self.media_manager.get_pending_media_by_id(media_id)

            if not media:
                await query.edit_message_text("این مدیا قبلاً پردازش شده یا یافت نشد.")
                logger.info(f"Admin {user_id} tried to approve non-existent media {media_id}.")
                return

            user_profile = self.user_manager.get_user_profile(media.user_id)
            display_name = user_profile.display_name if user_profile else f"کاربر ناشناس ({media.user_id})"
            
            # Post media to channel
            try:
                caption_to_post = f"**{display_name}**: {media.caption}" if media.caption else f"**{display_name}**"

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
                else:
                    await query.edit_message_text(f"نوع مدیا '{media.media_type}' برای انتشار پشتیبانی نمی‌شود.")
                    logger.error(f"Unsupported media type for posting: {media.media_type}")
                    return

                self.media_manager.approve_media(media_id, user_id)
                self.user_manager.increment_message_count(media.user_id)
                self.stats["media_approved"] += 1
                
                await query.edit_message_text(f"مدیا (ID: {media_id}) با موفقیت تأیید و منتشر شد.")
                logger.info(f"Admin {user_id} approved media {media_id}. Posted to channel.")
                
                # Notify original user that their media was approved
                await context.bot.send_message(
                    chat_id=media.user_id,
                    text="رسانه شما توسط ادمین تأیید و در کانال منتشر شد.",
                    reply_markup=self._get_main_menu_keyboard(self.config.is_admin(media.user_id))
                )

            except TelegramError as e:
                await query.edit_message_text(f"خطا در انتشار مدیا (ID: {media_id}): {e}")
                logger.error(f"Error posting approved media {media_id} to channel: {e}")

        elif data.startswith("reject_media_"):
            media_id = data.replace("reject_media_", "")
            media = self.media_manager.get_pending_media_by_id(media_id)

            if not media:
                await query.edit_message_text("این مدیا قبلاً پردازش شده یا یافت نشد.")
                logger.info(f"Admin {user_id} tried to reject non-existent media {media_id}.")
                return

            self.media_manager.reject_media(media_id, user_id)
            self.stats["media_rejected"] += 1
            await query.edit_message_text(f"مدیا (ID: {media_id}) رد شد.")
            logger.info(f"Admin {user_id} rejected media {media_id}.")

            # Notify original user that their media was rejected
            await context.bot.send_message(
                chat_id=media.user_id,
                text="رسانه شما توسط ادمین رد شد.",
                reply_markup=self._get_main_menu_keyboard(self.config.is_admin(media.user_id))
            )

    async def admin_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin_stats command to show bot statistics to admins"""
        user = update.effective_user
        if not user or not self.config.is_admin(user.id):
            if update.message:
                await update.message.reply_text("شما اجازه دسترسی به این فرمان را ندارید.")
            elif update.callback_query:
                await update.callback_query.edit_message_text("شما اجازه دسترسی به این فرمان را ندارید.")
            logger.warning(f"Non-admin user {user.id} tried to access /admin_stats or admin stats from menu.")
            return

        media_stats = self.media_manager.get_media_stats()
        user_stats = self.user_manager.get_user_stats()

        stats_message = f"""
📊 **آمار ربات:**

**پیام‌ها:**
• پردازش شده: `{self.stats['messages_processed']}`
• فیلتر شده (به دلیل کلمات نامناسب): `{self.stats['messages_filtered']}`
• منتشر شده در کانال: `{self.stats['messages_posted']}`

**مدیا (عکس، ویدئو و...):**
• در انتظار تأیید: `{media_stats['pending']}`
• تأیید شده: `{media_stats['approved']}`
• رد شده: `{media_stats['rejected']}`

**کاربران:**
• کل کاربران: `{user_stats['total_users']}`
• دارای نام نمایشی سفارشی: `{user_stats['custom_names']}`
• دارای نام نمایشی پیش‌فرض: `{user_stats['default_names']}`
• کل پیام‌های ارسالی توسط کاربران: `{user_stats['total_messages']}`
"""
        if update.message:
            await update.message.reply_text(stats_message, parse_mode='Markdown', reply_markup=self._get_main_menu_keyboard(True))
        elif update.callback_query:
            await update.callback_query.edit_message_text(stats_message, parse_mode='Markdown', reply_markup=self._get_main_menu_keyboard(True))
        logger.info(f"Admin {user.id} requested bot statistics.")

    async def add_profanity_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_profanity command for admins to add words"""
        user = update.effective_user
        if not user or not self.config.is_admin(user.id):
            if update.message:
                await update.message.reply_text("شما اجازه دسترسی به این فرمان را ندارید.")
            logger.warning(f"Non-admin user {user.id} tried to access /add_profanity.")
            return

        if not context.args or len(context.args) < 2:
            if update.message:
                await update.message.reply_text(
                    "نحوه استفاده: `/add_profanity <کلمه> <زبان>`\n"
                    "مثال: `/add_profanity شیطون فارسی` (برای اضافه کردن یک کلمه فارسی)\n"
                    "مثال: `/add_profanity shitoon farsi_latin` (برای اضافه کردن فینگلیش)\n"
                    "زبان‌های پشتیبانی شده: `english`, `persian`, `farsi_latin`",
                    parse_mode='Markdown',
                    reply_markup=self._get_main_menu_keyboard(True)
                )
            return

        word = context.args[0].lower()
        language = context.args[1].lower()

        if language not in ["english", "persian", "farsi_latin"]:
            await update.message.reply_text(
                "زبان نامعتبر. زبان‌های پشتیبانی شده: `english`, `persian`, `farsi_latin`",
                parse_mode='Markdown',
                reply_markup=self._get_main_menu_keyboard(True)
            )
            return

        if language not in self.profanity_filter.profanity_words:
            self.profanity_filter.profanity_words[language] = []

        if word in self.profanity_filter.profanity_words[language]:
            await update.message.reply_text(f"کلمه `{word}` قبلاً در لیست کلمات نامناسب `{language}` وجود دارد.", parse_mode='Markdown', reply_markup=self._get_main_menu_keyboard(True))
            logger.info(f"Admin {user.id} tried to add existing profanity word '{word}' in '{language}'.")
            return

        self.profanity_filter.add_word(word, language)
        await update.message.reply_text(f"کلمه `{word}` با موفقیت به لیست کلمات نامناسب `{language}` اضافه شد.", parse_mode='Markdown', reply_markup=self._get_main_menu_keyboard(True))
        logger.info(f"Admin {user.id} added profanity word '{word}' to '{language}'.")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log Errors caused by Updates."""
        logger.error(f"Update {update} caused error {context.error}")

# You would need to add this to your main.py if not already present
# and ensure proper handler registration