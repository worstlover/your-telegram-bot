import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.client.default import DefaultBotProperties # Make sure this is imported

# Assuming badwords.py exists and contains_bad_words is defined there
from badwords import contains_bad_words

# --- Configuration ---
API_TOKEN = "8463214619:AAE5HLwJQERrFltZ6cBz7sanSZVOMdwe1D0" # Use your actual token here
CHANNEL_ID = -1002711756571  # Numerical ID of your channel
ADMIN_IDS = [6675766939]  # Numerical IDs of your admins
MAIN_ADMIN_ID = 6675766939 # For logging which admin approved

NEED_APPROVAL_TEXT = True    # If True, text messages need approval
NEED_APPROVAL_MEDIA = True   # If True, media also needs approval

logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
# --- CORRECTED LINE BELOW ---
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
# --- CORRECTED LINE ABOVE ---
dp = Dispatcher() # Only one Dispatcher instance

pending_messages = {}  # To hold messages awaiting approval

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("سلام! پیام متنی یا مدیا بفرست تا به کانال منتقل کنم.")

@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text or ""

    # Filter bad words
    if contains_bad_words(text):
        await message.reply("🚫 پیام شما شامل محتوای نامناسب است و حذف شد.")
        return

    # If it's media
    if message.photo or message.video or message.document:
        if NEED_APPROVAL_MEDIA:
            await ask_approval(message, is_media=True)
        else:
            await forward_to_channel(message, approved_by=None)
    else:
        # Text
        if NEED_APPROVAL_TEXT:
            await ask_approval(message, is_media=False)
        else:
            await forward_to_channel(message, approved_by=None)

async def ask_approval(message: types.Message, is_media: bool):
    msg_id = message.message_id
    pending_messages[msg_id] = message

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="✅ تایید", callback_data=f"approve_{msg_id}"),
        InlineKeyboardButton(text="❌ رد", callback_data=f"reject_{msg_id}")
    )

    caption = message.caption or message.text or "[بدون متن]"
    preview = f"درخواست {'مدیا' if is_media else 'متنی'}:\n\n{caption}"

    # Send to all admins
    for admin_id in ADMIN_IDS:
        try:
            if message.photo:
                await bot.send_photo(admin_id, photo=message.photo[-1].file_id,
                                     caption=preview, reply_markup=keyboard.as_markup())
            elif message.video:
                await bot.send_video(admin_id, video=message.video.file_id,
                                     caption=preview, reply_markup=keyboard.as_markup())
            elif message.document:
                await bot.send_document(admin_id, document=message.document.file_id,
                                         caption=preview, reply_markup=keyboard.as_markup())
            else:
                await bot.send_message(admin_id, text=preview,
                                         reply_markup=keyboard.as_markup())
        except Exception as e:
            print(f"خطا در ارسال برای مدیر {admin_id}: {e}")

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    data = callback.data
    if data.startswith("approve_"):
        msg_id = int(data.split("_")[1])
        message = pending_messages.pop(msg_id, None)
        if message:
            await forward_to_channel(message, approved_by=callback.from_user.id)
            await callback.message.edit_text("✅ پیام تأیید و ارسال شد.")
    elif data.startswith("reject_"):
        msg_id = int(data.split("_")[1])
        if msg_id in pending_messages:
            pending_messages.pop(msg_id)
            await callback.message.edit_text("❌ پیام رد شد.")

async def forward_to_channel(message: types.Message, approved_by=None):
    text = message.caption or message.text or ""
    extra_note = ""
    if approved_by:
        extra_note = f"\n\n✅ تایید شده توسط: <code>{approved_by}</code>"

    try:
        if message.photo:
            await bot.send_photo(CHANNEL_ID, photo=message.photo[-1].file_id,
                                 caption=text + extra_note)
        elif message.video:
            await bot.send_video(CHANNEL_ID, video=message.video.file_id,
                                 caption=text + extra_note)
        elif message.document:
            await bot.send_document(CHANNEL_ID, document=message.document.file_id,
                                     caption=text + extra_note)
        else:
            await bot.send_message(CHANNEL_ID, text + extra_note)

        if approved_by:
            await bot.send_message(MAIN_ADMIN_ID,
                                   f"📬 پیام توسط مدیر <code>{approved_by}</code> تایید و ارسال شد.")
    except Exception as e:
        await message.reply("❌ خطا در ارسال به کانال.")
        print(e)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())