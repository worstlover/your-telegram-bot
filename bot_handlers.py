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
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        if not user:
            return
        
        # Register or get user profile
        user_profile = self.user_manager.register_user(user.id, user.username or user.first_name or "Unknown")
        
        # Create keyboard for name setting
        keyboard = [
            [InlineKeyboardButton("تنظیم نام نمایشی", callback_data="set_display_name")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
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
            await update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)
        logger.info(f"User {user.id} ({user.username or user.first_name}) started the bot")
    
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
• بعد از تایید بدون نام شما در کانال منتشر خواهد شد

**حریم خصوصی:**
🔒 تمام پیام‌ها کاملاً ناشناس منتشر می‌شوند
📝 هیچ اطلاعاتی از شما ثبت نمی‌شود
⚡ پیام‌های متنی فوری منتشر می‌شوند

**دستورات ادمین:**
/pending - مشاهده رسانه‌های در انتظار تایید
/stats - آمار عملکرد ربات

**توجه:** از ارسال محتوای نامناسب خودداری کنید.
        """
        
        if update.message:
            await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def pending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pending command (admin only)"""
        if not update.effective_user or not update.message:
            return
            
        user_id = update.effective_user.id
        
        if not self.config.is_admin(user_id):
            await update.message.reply_text("❌ این دستور فقط برای ادمین هاست.")
            return
        
        pending_media = self.media_manager.get_pending_media()
        
        if not pending_media:
            await update.message.reply_text("✅ هیچ رسانه ای در انتظار تایید نیست.")
            return
        
        message = f"📋 **رسانه های در انتظار تایید:** {len(pending_media)}\n\n"
        
        for i, media in enumerate(pending_media[:10], 1):  # Show first 10
            time_ago = int((time.time() - media.timestamp) / 60)
            message += f"{i}. **{media.media_type}** از @{media.username}\n"
            message += f"   📅 {time_ago} دقیقه پیش\n"
            if media.caption:
                caption_preview = media.caption[:50] + "..." if len(media.caption) > 50 else media.caption
                message += f"   💬 {caption_preview}\n"
            message += f"   🆔 `{media.id}`\n\n"
        
        if len(pending_media) > 10:
            message += f"... و {len(pending_media) - 10} مورد دیگر"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command (admin only)"""
        if not update.effective_user or not update.message:
            return
            
        user_id = update.effective_user.id
        
        if not self.config.is_admin(user_id):
            await update.message.reply_text("❌ این دستور فقط برای ادمین هاست.")
            return
        
        media_stats = self.media_manager.get_stats()
        user_stats = self.user_manager.get_user_stats()
        
        stats_message = f"""
📊 **آمار عملکرد ربات**

**پیام های متنی:**
• پردازش شده: {self.stats['messages_processed']}
• فیلتر شده: {self.stats['messages_filtered']}
• منتشر شده: {self.stats['messages_posted']}

**کاربران:**
• کل کاربران: {user_stats['total_users']}
• نام‌های انتخابی: {user_stats['custom_names']}
• شماره‌های خودکار: {user_stats['default_names']}
• کل پیام‌ها: {user_stats['total_messages']}

**رسانه ها:**
• در انتظار: {media_stats['pending']}
• تایید شده: {media_stats['approved']}
• رد شده: {media_stats['rejected']}
• کل: {media_stats['total']}

**انواع رسانه:**
"""
        
        for media_type, count in media_stats['media_types'].items():
            stats_message += f"• {media_type}: {count}\n"
        
        if media_stats['oldest_pending']:
            oldest_minutes = int((time.time() - media_stats['oldest_pending']) / 60)
            stats_message += f"\n⏰ قدیمی ترین رسانه در انتظار: {oldest_minutes} دقیقه پیش"
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        if not update.effective_user or not update.message or not update.message.text:
            return
            
        user = update.effective_user
        message = update.message
        text = message.text
        assert text is not None  # We already checked this in the condition above
        
        self.stats['messages_processed'] += 1
        
        # Check if user is setting display name
        if self.user_manager.is_setting_name(user.id):
            success, msg = self.user_manager.set_display_name(user.id, text)
            await message.reply_text(msg)
            return
        
        # Get or register user profile
        user_profile = self.user_manager.get_user(user.id)
        if not user_profile:
            user_profile = self.user_manager.register_user(user.id, user.username or user.first_name or "Unknown")
        
        logger.info(f"Processing text message from {user.username or user.first_name} ({user.id})")
        
        try:
            # Check for profanity
            has_profanity, found_words = self.profanity_filter.contains_profanity(text)
            
            if has_profanity:
                self.stats['messages_filtered'] += 1
                logger.warning(f"Filtered message from {user.username or user.first_name}: found words {found_words}")
                
                # Notify user about filtered content
                await message.reply_text(
                    "❌ پیام شما حاوی محتوای نامناسب است و منتشر نخواهد شد.\n"
                    "لطفاً از کلمات مناسب استفاده کنید."
                )
                return
            
            # Get severity score
            severity = self.profanity_filter.get_severity_score(text)
            if severity > 3:  # Additional check for borderline content
                self.stats['messages_filtered'] += 1
                logger.warning(f"Message from {user.username or user.first_name} has high severity score: {severity}")
                
                await message.reply_text(
                    "⚠️ پیام شما ممکن است محتوای نامناسب داشته باشد و منتشر نخواهد شد."
                )
                return
            
            # Message is clean, post to channel with display name
            await self._post_to_channel_with_name(context, text, user_profile.display_name)
            
            self.stats['messages_posted'] += 1
            self.user_manager.increment_message_count(user.id)
            
            # Confirm to user
            await message.reply_text(
                f"✅ پیام شما با نام '{user_profile.display_name}' در کانال منتشر شد.\n\n"
                "🔒 فقط نام نمایشی شما نمایش داده می‌شود.\n"
                "📝 اطلاعات شخصی شما ثبت نمی‌شود.\n"
                "⚡ پیام‌های متنی مستقیماً در کانال درج می‌شوند."
            )
            
        except Exception as e:
            logger.error(f"Error processing text message: {e}")
            await message.reply_text("❌ خطا در پردازش پیام. لطفاً دوباره تلاش کنید.")
    
    async def handle_media_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming media messages"""
        if not update.effective_user or not update.message:
            return
            
        user = update.effective_user
        message = update.message
        
        # Get or register user profile
        user_profile = self.user_manager.get_user(user.id)
        if not user_profile:
            user_profile = self.user_manager.register_user(user.id, user.username or user.first_name or "Unknown")
        
        logger.info(f"Processing media message from {user.username or user.first_name} ({user.id})")
        
        try:
            # Determine media type and get file_id
            media_type, file_id = self._get_media_info(message)
            
            if not file_id:
                await message.reply_text("❌ نوع رسانه پشتیبانی نمی شود.")
                return
            
            # Check user's pending media count
            user_pending = self.media_manager.get_user_pending_count(user.id)
            if user_pending >= 5:  # Limit per user
                await message.reply_text(
                    "⚠️ شما بیش از حد مجاز رسانه در انتظار تایید دارید.\n"
                    "لطفاً منتظر تایید موارد قبلی باشید."
                )
                return
            
            # Get caption if exists
            caption = message.caption or ""
            
            # Check caption for profanity
            if caption:
                has_profanity, found_words = self.profanity_filter.contains_profanity(caption)
                if has_profanity:
                    await message.reply_text(
                        "❌ متن همراه رسانه حاوی محتوای نامناسب است.\n"
                        "لطفاً متن را اصلاح کرده و دوباره ارسال کنید."
                    )
                    return
            
            # Add to pending media
            media_id = self.media_manager.add_pending_media(
                user_id=user.id,
                username=user.username or user.first_name,
                message_id=message.message_id,
                media_type=media_type,
                file_id=file_id,
                caption=caption
            )
            
            self.stats['media_pending'] += 1
            
            # Send to admin for approval
            await self._send_media_for_approval(context, media_id)
            
            # Confirm to user
            await message.reply_text(
                "📋 رسانه شما دریافت شد و برای تایید نزد ادمین ارسال شد.\n\n"
                "🔒 رسانه شما کاملاً ناشناس منتشر خواهد شد.\n"
                "📝 هیچ اطلاعاتی از شما ثبت یا ذخیره نمی‌شود.\n"
                "⏳ بعد از تایید ادمین در کانال منتشر خواهد شد."
            )
            
        except Exception as e:
            logger.error(f"Error processing media message: {e}")
            await message.reply_text("❌ خطا در پردازش رسانه. لطفاً دوباره تلاش کنید.")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button presses"""
        query = update.callback_query
        if not query or not query.data:
            return
            
        await query.answer()
        
        # Handle display name setting
        if query.data == "set_display_name":
            self.user_manager.start_name_setting(query.from_user.id)
            await query.edit_message_text(
                "✏️ **تنظیم نام نمایشی**\n\n"
                "لطفاً نام نمایشی مورد نظر خود را ارسال کنید:\n\n"
                "⚠️ **توجه:**\n"
                "• نام نمایشی بعد از تنظیم قابل تغییر نیست\n"
                "• حداکثر 20 کاراکتر\n"
                "• نباید شامل کلمات نامناسب باشد\n"
                "• نباید تکراری باشد\n\n"
                "برای لغو، دستور /start را ارسال کنید.",
                parse_mode='Markdown'
            )
            return
        
        # Admin approval handlers
        if not self.config.is_admin(query.from_user.id):
            await query.edit_message_text("❌ شما مجاز به این عمل نیستید.")
            return
        
        try:
            action, media_id = query.data.split("_", 1)
            
            if action in ["approve", "reject"]:
                media = self.media_manager.get_media_by_id(media_id)
                
                if media:
                    if action == "approve":
                        # Post to channel with display name
                        await self._post_media_to_channel_with_name(context, media)
                        
                        # Update stats
                        self.stats['media_approved'] += 1
                        
                        # Notify user
                        try:
                            user_profile = self.user_manager.get_user(media.user_id)
                            display_name = user_profile.display_name if user_profile else "کاربر ناشناس"
                            
                            await context.bot.send_message(
                                chat_id=media.user_id,
                                text=f"✅ رسانه شما با نام '{display_name}' تایید و در کانال منتشر شد.\n\n"
                                     "🔒 فقط نام نمایشی شما نمایش داده می‌شود.\n"
                                     "📝 اطلاعات شخصی شما ثبت نمی‌شود."
                            )
                        except:
                            pass  # User might have blocked bot
                        
                        await query.edit_message_text(f"✅ رسانه از @{media.username} تایید و منتشر شد.")
                    
                    else:  # reject
                        self.stats['media_rejected'] += 1
                        
                        # Notify user
                        try:
                            await context.bot.send_message(
                                chat_id=media.user_id,
                                text="❌ رسانه شما توسط ادمین رد شد.\n"
                                     "دلیل ممکن است محتوای نامناسب یا مغایر با قوانین کانال باشد."
                            )
                        except:
                            pass  # User might have blocked bot
                        
                        await query.edit_message_text(f"❌ رسانه از @{media.username} رد شد.")
                    
                    # Remove from pending
                    self.media_manager.remove_processed_media(media_id)
                else:
                    await query.edit_message_text("❌ رسانه مورد نظر یافت نشد.")
            
        except Exception as e:
            logger.error(f"Error in media approval callback: {e}")
            await query.edit_message_text("❌ خطا در پردازش تایید/رد.")
    
    async def media_approval_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle media approval/rejection callbacks - deprecated, using button_callback now"""
        await self.button_callback(update, context)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle bot errors"""
        logger.error(f"Bot error: {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ خطایی رخ داد. لطفاً دوباره تلاش کنید."
                )
            except:
                pass  # Ignore if we can't send error message
    
    def _get_media_info(self, message) -> tuple:
        """Extract media type and file_id from message"""
        if message.photo:
            return "photo", message.photo[-1].file_id
        elif message.video:
            return "video", message.video.file_id
        elif message.audio:
            return "audio", message.audio.file_id
        elif message.voice:
            return "voice", message.voice.file_id
        elif message.document:
            return "document", message.document.file_id
        elif message.animation:
            return "animation", message.animation.file_id
        elif message.sticker:
            return "sticker", message.sticker.file_id
        
        return None, None
    
    async def _post_to_channel(self, context: ContextTypes.DEFAULT_TYPE, text: str, user):
        """Post text message to channel"""
        try:
            # Post message without user attribution (anonymous)
            await context.bot.send_message(
                chat_id=self.config.CHANNEL_ID,
                text=text
            )
            
            logger.info(f"Posted anonymous text message to channel")
            
        except TelegramError as e:
            logger.error(f"Error posting to channel: {e}")
            raise
    
    async def _post_to_channel_with_name(self, context: ContextTypes.DEFAULT_TYPE, text: str, display_name: str):
        """Post text message to channel with display name"""
        try:
            # Post message with display name
            formatted_text = f"📝 {display_name}:\n\n{text}"
            await context.bot.send_message(
                chat_id=self.config.CHANNEL_ID,
                text=formatted_text
            )
            
            logger.info(f"Posted text message to channel from {display_name}")
            
        except TelegramError as e:
            logger.error(f"Error posting to channel: {e}")
            raise
    
    async def _post_media_to_channel(self, context: ContextTypes.DEFAULT_TYPE, media: PendingMedia):
        """Post approved media to channel"""
        try:
            # Use original caption without user attribution (anonymous)
            caption = media.caption or None
            
            # Send based on media type
            if media.media_type == "photo":
                await context.bot.send_photo(
                    chat_id=self.config.CHANNEL_ID,
                    photo=media.file_id,
                    caption=caption
                )
            elif media.media_type == "video":
                await context.bot.send_video(
                    chat_id=self.config.CHANNEL_ID,
                    video=media.file_id,
                    caption=caption
                )
            elif media.media_type == "audio":
                await context.bot.send_audio(
                    chat_id=self.config.CHANNEL_ID,
                    audio=media.file_id,
                    caption=caption
                )
            elif media.media_type == "voice":
                await context.bot.send_voice(
                    chat_id=self.config.CHANNEL_ID,
                    voice=media.file_id,
                    caption=caption
                )
            elif media.media_type == "document":
                await context.bot.send_document(
                    chat_id=self.config.CHANNEL_ID,
                    document=media.file_id,
                    caption=caption
                )
            elif media.media_type == "animation":
                await context.bot.send_animation(
                    chat_id=self.config.CHANNEL_ID,
                    animation=media.file_id,
                    caption=caption
                )
            elif media.media_type == "sticker":
                await context.bot.send_sticker(
                    chat_id=self.config.CHANNEL_ID,
                    sticker=media.file_id
                )
                # Send caption separately for stickers
                if caption:
                    await context.bot.send_message(
                        chat_id=self.config.CHANNEL_ID,
                        text=caption
                    )
            
            logger.info(f"Posted {media.media_type} to channel from {media.username}")
            
        except TelegramError as e:
            logger.error(f"Error posting media to channel: {e}")
            raise
    
    async def _post_media_to_channel_with_name(self, context: ContextTypes.DEFAULT_TYPE, media: PendingMedia):
        """Post approved media to channel with display name"""
        try:
            # Get user display name
            user_profile = self.user_manager.get_user(media.user_id)
            display_name = user_profile.display_name if user_profile else "کاربر ناشناس"
            
            # Format caption with display name
            if media.caption:
                caption = f"📸 {display_name}:\n\n{media.caption}"
            else:
                caption = f"📸 {display_name}"
            
            # Send based on media type
            if media.media_type == "photo":
                await context.bot.send_photo(
                    chat_id=self.config.CHANNEL_ID,
                    photo=media.file_id,
                    caption=caption
                )
            elif media.media_type == "video":
                await context.bot.send_video(
                    chat_id=self.config.CHANNEL_ID,
                    video=media.file_id,
                    caption=caption
                )
            elif media.media_type == "audio":
                await context.bot.send_audio(
                    chat_id=self.config.CHANNEL_ID,
                    audio=media.file_id,
                    caption=caption
                )
            elif media.media_type == "voice":
                await context.bot.send_voice(
                    chat_id=self.config.CHANNEL_ID,
                    voice=media.file_id,
                    caption=caption
                )
            elif media.media_type == "document":
                await context.bot.send_document(
                    chat_id=self.config.CHANNEL_ID,
                    document=media.file_id,
                    caption=caption
                )
            elif media.media_type == "animation":
                await context.bot.send_animation(
                    chat_id=self.config.CHANNEL_ID,
                    animation=media.file_id,
                    caption=caption
                )
            elif media.media_type == "sticker":
                await context.bot.send_sticker(
                    chat_id=self.config.CHANNEL_ID,
                    sticker=media.file_id
                )
                # Send caption separately for stickers
                await context.bot.send_message(
                    chat_id=self.config.CHANNEL_ID,
                    text=caption
                )
            
            # Increment user message count
            self.user_manager.increment_message_count(media.user_id)
            
            logger.info(f"Posted {media.media_type} to channel from {display_name}")
            
        except TelegramError as e:
            logger.error(f"Error posting media to channel: {e}")
            raise
    
    async def _send_media_for_approval(self, context: ContextTypes.DEFAULT_TYPE, media_id: str):
        """Send media to admin for approval"""
        media = self.media_manager.get_media_by_id(media_id)
        if not media:
            return
        
        try:
            # Create approval keyboard
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ تایید", callback_data=f"approve_{media_id}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"reject_{media_id}")
                ]
            ])
            
            # Send media with approval buttons
            approval_text = (
                f"📋 **درخواست تایید رسانه**\n\n"
                f"👤 کاربر: @{media.username}\n"
                f"📅 زمان: {time.strftime('%Y-%m-%d %H:%M', time.localtime(media.timestamp))}\n"
                f"🎯 نوع: {media.media_type}\n"
                f"📝 متن: {media.caption or 'بدون متن'}\n\n"
                f"🆔 `{media_id}`"
            )
            
            # Send the actual media first
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
            else:
                # For other media types, send as document and then approval message
                if media.media_type == "audio":
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
                await context.bot.send_message(
                    chat_id=self.config.ADMIN_USER_ID,
                    text=approval_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            
            logger.info(f"Sent media {media_id} to admin for approval")
            
        except TelegramError as e:
            logger.error(f"Error sending media for approval: {e}")
