import os
import logging
import asyncio
from collections import deque

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

waiting_users = deque()
partners = {}
searching = set()

def main_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔎 Find Stranger", callback_data="find"))
    return kb

def chat_keyboard():
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("⏭ Next", callback_data="next"),
        InlineKeyboardButton("🛑 Stop", callback_data="stop"),
        InlineKeyboardButton("🚨 Report", callback_data="report"),
    )
    return kb

async def send_main_menu(user_id):
    await bot.send_message(
        user_id,
        "👋 <b>Anonymous Chat</b>\n\nTalk anonymously with a random stranger.\n\nPress <b>Find Stranger</b> to start.",
        reply_markup=main_keyboard(),
    )

async def remove_from_queue(user_id):
    searching.discard(user_id)
    try:
        waiting_users.remove(user_id)
    except ValueError:
        pass

async def end_chat(user_id, notify_partner=True):
    partner_id = partners.pop(user_id, None)
    if partner_id is None:
        return None
    partners.pop(partner_id, None)
    if notify_partner:
        try:
            await bot.send_message(
                partner_id,
                "❌ <b>Stranger left the chat.</b>\n\nYou can find another stranger below.",
                reply_markup=main_keyboard(),
            )
        except Exception as e:
            logging.error("Could not notify partner %s: %s", partner_id, e)
    return partner_id

async def find_match(user_id):
    if user_id in partners:
        await bot.send_message(user_id, "💬 You are already chatting with a stranger.", reply_markup=chat_keyboard())
        return
    if user_id in searching:
        await bot.send_message(user_id, "🔎 You are already searching for a stranger...")
        return

    while waiting_users:
        partner_id = waiting_users.popleft()
        if partner_id == user_id:
            continue
        if partner_id not in searching:
            continue

        searching.discard(partner_id)
        partners[user_id] = partner_id
        partners[partner_id] = user_id

        await bot.send_message(user_id, "🎉 <b>Stranger found!</b>\n\nYou are now connected anonymously.\nSend a message to start chatting.", reply_markup=chat_keyboard())
        await bot.send_message(partner_id, "🎉 <b>Stranger found!</b>\n\nYou are now connected anonymously.\nSend a message to start chatting.", reply_markup=chat_keyboard())
        logging.info("MATCH: %s <-> %s", user_id, partner_id)
        return

    searching.add(user_id)
    waiting_users.append(user_id)
    await bot.send_message(user_id, "🔎 <b>Searching for a stranger...</b>\n\nPlease wait. I'll connect you when someone is available.", reply_markup=main_keyboard())
    logging.info("SEARCHING: %s | queue=%s", user_id, len(waiting_users))

@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in partners:
        await message.answer("💬 You are already chatting with a stranger.", reply_markup=chat_keyboard())
        return
    if user_id in searching:
        await message.answer("🔎 You are already searching for a stranger...")
        return
    await send_main_menu(user_id)

@dp.message_handler(commands=["next"])
async def next_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in searching:
        await message.answer("🔎 You are already searching...")
        return
    if user_id in partners:
        await end_chat(user_id, notify_partner=True)
        await message.answer("⏭ <b>Finding a new stranger...</b>")
        await find_match(user_id)
        return
    await find_match(user_id)

@dp.message_handler(commands=["stop"])
async def stop_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in searching:
        await remove_from_queue(user_id)
        await message.answer("🛑 <b>Search stopped.</b>", reply_markup=main_keyboard())
        return
    if user_id in partners:
        await end_chat(user_id, notify_partner=True)
        await message.answer("🛑 <b>Chat ended.</b>", reply_markup=main_keyboard())
        return
    await message.answer("You are not currently in a chat.", reply_markup=main_keyboard())

@dp.message_handler(commands=["report"])
async def report_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in partners:
        await message.answer("You are not currently chatting with anyone.")
        return
    partner_id = partners.get(user_id)
    logging.warning("REPORT: user %s reported user %s", user_id, partner_id)
    await end_chat(user_id, notify_partner=True)
    await message.answer("🚨 <b>Report submitted.</b>\n\nThe chat has been ended.", reply_markup=main_keyboard())

@dp.callback_query_handler(lambda callback: callback.data == "find")
async def find_button(callback: types.CallbackQuery):
    await callback.answer()
    await find_match(callback.from_user.id)

@dp.callback_query_handler(lambda callback: callback.data == "next")
async def next_button(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id in partners:
        await end_chat(user_id, notify_partner=True)
    elif user_id in searching:
        await callback.message.answer("🔎 You are already searching...")
        return
    await callback.message.answer("⏭ <b>Finding a new stranger...</b>")
    await find_match(user_id)

@dp.callback_query_handler(lambda callback: callback.data == "stop")
async def stop_button(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id in searching:
        await remove_from_queue(user_id)
    elif user_id in partners:
        await end_chat(user_id, notify_partner=True)
    await callback.message.answer("🛑 <b>Chat stopped.</b>\n\nPress Find Stranger to start again.", reply_markup=main_keyboard())

@dp.callback_query_handler(lambda callback: callback.data == "report")
async def report_button(callback: types.CallbackQuery):
    await callback.answer("Report submitted.")
    user_id = callback.from_user.id
    if user_id not in partners:
        await callback.message.answer("You are not currently chatting with anyone.")
        return
    partner_id = partners.get(user_id)
    logging.warning("REPORT: user %s reported user %s", user_id, partner_id)
    await end_chat(user_id, notify_partner=True)
    await callback.message.answer("🚨 <b>Report submitted.</b>\n\nThe chat has been ended.", reply_markup=main_keyboard())

@dp.message_handler(content_types=types.ContentTypes.ANY)
async def relay_message(message: types.Message):
    user_id = message.from_user.id
    if message.text and message.text.startswith("/"):
        return
    partner_id = partners.get(user_id)
    if not partner_id:
        await message.answer("You are not currently chatting with anyone.\n\nPress <b>Find Stranger</b> to start.", reply_markup=main_keyboard())
        return
    try:
        await bot.copy_message(chat_id=partner_id, from_chat_id=user_id, message_id=message.message_id)
    except Exception as e:
        logging.error("Message relay failed: %s", e)
        await message.answer("⚠️ I couldn't send that message.")

async def on_startup(dispatcher):
    me = await bot.get_me()
    logging.info("Anonymous Chat Bot started: @%s", me.username)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
