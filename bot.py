import os
import logging
import asyncio
from collections import deque

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

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
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(KeyboardButton("🔎 Find Stranger"))
    return kb

def chat_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add(
        KeyboardButton("⏭️ Next"),
        KeyboardButton("🛑 Stop"),
        KeyboardButton("🚨 Report"),
    )
    return kb

async def send_main_menu(user_id):
    await bot.send_message(
        user_id,
        "👋 <b>Welcome to Anonymous Chat</b>\n\n"
        "🕵️ Talk anonymously with random people.\n"
        "🔒 Your identity stays private.\n"
        "🌍 Meet someone new from anywhere.\n\n"
        "🔎 <b>Find a Stranger</b> to start chatting!",
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
                "❌ <b>Stranger left the chat.</b>\n\n"
                "💬 You can find someone new below.",
                reply_markup=main_keyboard(),
            )
        except Exception as e:
            logging.error("Could not notify partner %s: %s", partner_id, e)
    return partner_id

async def find_match(user_id):
    if user_id in partners:
        await bot.send_message(
            user_id,
            "💬 <b>You are already chatting with a stranger.</b>",
            reply_markup=chat_keyboard(),
        )
        return
    if user_id in searching:
        await bot.send_message(user_id, "🔎 <b>You are already searching...</b>")
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

        match_text = (
            "🎉 <b>Stranger Found!</b>\n\n"
            "🔒 You are now connected anonymously.\n"
            "💬 Say hello and start chatting!\n\n"
            "🛡️ Stay anonymous. Have fun!"
        )

        await bot.send_message(
            user_id,
            match_text,
            reply_markup=chat_keyboard(),
        )
        await bot.send_message(
            partner_id,
            match_text,
            reply_markup=chat_keyboard(),
        )
        logging.info("MATCH: %s <-> %s", user_id, partner_id)
        return

    searching.add(user_id)
    waiting_users.append(user_id)
    await bot.send_message(
        user_id,
        "🔎 <b>Looking for a stranger...</b>\n\n"
        "⏳ Please wait while we find someone for you.",
        reply_markup=main_keyboard(),
    )
    logging.info("SEARCHING: %s | queue=%s", user_id, len(waiting_users))

@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in partners:
        await message.answer(
            "💬 <b>You are already chatting with a stranger.</b>",
            reply_markup=chat_keyboard(),
        )
        return
    if user_id in searching:
        await message.answer("🔎 <b>You are already searching...</b>")
        return
    await send_main_menu(user_id)

@dp.message_handler(commands=["next"])
async def next_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in searching:
        await message.answer("🔎 <b>You are already searching...</b>")
        return
    if user_id in partners:
        await end_chat(user_id, notify_partner=True)
        await message.answer("⏭️ <b>Finding someone new...</b>")
        await find_match(user_id)
        return
    await find_match(user_id)

@dp.message_handler(commands=["stop"])
async def stop_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in searching:
        await remove_from_queue(user_id)
        await message.answer(
            "🛑 <b>Search stopped.</b>\n\n"
            "🔎 Press <b>Find Stranger</b> to start again.",
            reply_markup=main_keyboard(),
        )
        return
    if user_id in partners:
        await end_chat(user_id, notify_partner=True)
        await message.answer(
            "🛑 <b>Chat ended.</b>\n\n"
            "🔎 Press <b>Find Stranger</b> to start again.",
            reply_markup=main_keyboard(),
        )
        return
    await message.answer(
        "ℹ️ You are not currently in a chat.",
        reply_markup=main_keyboard(),
    )

@dp.message_handler(commands=["report"])
async def report_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in partners:
        await message.answer("ℹ️ You are not currently chatting with anyone.")
        return
    partner_id = partners.get(user_id)
    logging.warning("REPORT: user %s reported user %s", user_id, partner_id)
    await end_chat(user_id, notify_partner=True)
    await message.answer(
        "🚨 <b>Report submitted.</b>\n\n"
        "🛑 The chat has been ended.",
        reply_markup=main_keyboard(),
    )

@dp.message_handler(content_types=types.ContentTypes.ANY)
async def relay_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text or ""

    if text == "🔎 Find Stranger":
        await find_match(user_id)
        return

    if text == "⏭️ Next":
        if user_id in partners:
            await end_chat(user_id, notify_partner=True)
            await message.answer("⏭️ <b>Finding someone new...</b>")
        elif user_id in searching:
            await message.answer("🔎 <b>You are already searching...</b>")
            return
        else:
            await message.answer("🔎 <b>Finding a stranger...</b>")
        await find_match(user_id)
        return

    if text == "🛑 Stop":
        if user_id in searching:
            await remove_from_queue(user_id)
        elif user_id in partners:
            await end_chat(user_id, notify_partner=True)
        await message.answer(
            "🛑 <b>Chat stopped.</b>\n\n"
            "🔎 Press <b>Find Stranger</b> to start again.",
            reply_markup=main_keyboard(),
        )
        return

    if text == "🚨 Report":
        if user_id not in partners:
            await message.answer(
                "ℹ️ You are not currently chatting with anyone.",
                reply_markup=main_keyboard(),
            )
            return
        partner_id = partners.get(user_id)
        logging.warning("REPORT: user %s reported user %s", user_id, partner_id)
        await end_chat(user_id, notify_partner=True)
        await message.answer(
            "🚨 <b>Report submitted.</b>\n\n"
            "🛑 The chat has been ended.",
            reply_markup=main_keyboard(),
        )
        return

    if text.startswith("/"):
        return

    partner_id = partners.get(user_id)
    if not partner_id:
        await message.answer(
            "💬 <b>You are not currently in a chat.</b>\n\n"
            "🔎 Press <b>Find Stranger</b> to start.",
            reply_markup=main_keyboard(),
        )
        return
    try:
        await bot.copy_message(
            chat_id=partner_id,
            from_chat_id=user_id,
            message_id=message.message_id,
        )
    except Exception as e:
        logging.error("Message relay failed: %s", e)
        await message.answer("⚠️ <b>I couldn't send that message.</b>")

async def health(request):
    return web.Response(text="Anonymous Chat Bot is running")

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info("Health server listening on port %s", port)

async def on_startup(dispatcher):
    me = await bot.get_me()
    logging.info("Anonymous Chat Bot started: @%s", me.username)
    await start_health_server()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
