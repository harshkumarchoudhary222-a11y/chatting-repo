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
user_languages = {}

LANGUAGES = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 हिन्दी",
    "es": "🇪🇸 Español",
    "pt": "🇧🇷 Português",
    "fr": "🇫🇷 Français",
    "ar": "🇸🇦 العربية",
    "ru": "🇷🇺 Русский",
}

TEXT = {
    "en": {
        "find": "🔎 Find Stranger",
        "language": "🌐 Language",
        "next": "⏭️ Next",
        "stop": "🛑 Stop",
        "report": "🚨 Report",
        "welcome": "👋 <b>Welcome to Anonymous Chat</b>\n\n🕵️ Talk anonymously with random people.\n🔒 Your identity stays private.\n🌍 Meet someone new from anywhere.\n\n🔎 <b>Find a Stranger</b> to start chatting!",
        "already_chat": "💬 <b>You are already chatting with a stranger.</b>",
        "already_search": "🔎 <b>You are already searching...</b>",
        "found": "🎉 <b>Stranger Found!</b>\n\n🔒 You are now connected anonymously.\n💬 Say hello and start chatting!\n\n🛡️ Stay anonymous. Have fun!",
        "searching": "🔎 <b>Looking for a stranger...</b>\n\n⏳ Please wait while we find someone for you.",
        "left": "❌ <b>Stranger left the chat.</b>\n\n💬 You can find someone new below.",
        "stopped": "🛑 <b>Chat stopped.</b>\n\n🔎 Press <b>Find Stranger</b> to start again.",
        "search_stopped": "🛑 <b>Search stopped.</b>\n\n🔎 Press <b>Find Stranger</b> to start again.",
        "not_chat": "ℹ️ You are not currently in a chat.",
        "report": "🚨 <b>Report submitted.</b>\n\n🛑 The chat has been ended.",
        "no_chat": "💬 <b>You are not currently in a chat.</b>\n\n🔎 Press <b>Find Stranger</b> to start.",
        "relay_error": "⚠️ <b>I couldn't send that message.</b>",
        "language_title": "🌐 <b>Choose your language</b>\n\nSelect the language you want to use in the bot.",
        "language_saved": "✅ <b>Language updated!</b>",
    },
    "hi": {
        "find": "🔎 अजनबी खोजें",
        "language": "🌐 भाषा",
        "next": "⏭️ अगला",
        "stop": "🛑 रोकें",
        "report": "🚨 रिपोर्ट",
        "welcome": "👋 <b>Anonymous Chat में आपका स्वागत है</b>\n\n🕵️ अनजान लोगों से गुमनाम चैट करें।\n🔒 आपकी पहचान निजी रहेगी।\n🌍 दुनिया भर के लोगों से मिलें।\n\n🔎 चैट शुरू करने के लिए <b>अजनबी खोजें</b> दबाएँ!",
        "already_chat": "💬 <b>आप पहले से एक अजनबी से चैट कर रहे हैं।</b>",
        "already_search": "🔎 <b>आप पहले से किसी को खोज रहे हैं...</b>",
        "found": "🎉 <b>अजनबी मिल गया!</b>\n\n🔒 अब आप गुमनाम रूप से जुड़े हैं।\n💬 नमस्ते कहकर चैट शुरू करें!\n\n🛡️ गुमनाम रहें और मज़े करें!",
        "searching": "🔎 <b>अजनबी खोजा जा रहा है...</b>\n\n⏳ कृपया प्रतीक्षा करें।",
        "left": "❌ <b>अजनबी चैट छोड़कर चला गया।</b>\n\n💬 आप किसी नए व्यक्ति को खोज सकते हैं।",
        "stopped": "🛑 <b>चैट रोक दी गई।</b>\n\n🔎 फिर से शुरू करने के लिए <b>अजनबी खोजें</b> दबाएँ।",
        "search_stopped": "🛑 <b>खोज रोक दी गई।</b>\n\n🔎 फिर से शुरू करने के लिए <b>अजनबी खोजें</b> दबाएँ।",
        "not_chat": "ℹ️ आप अभी किसी चैट में नहीं हैं।",
        "report": "🚨 <b>रिपोर्ट भेज दी गई।</b>\n\n🛑 चैट समाप्त कर दी गई है।",
        "no_chat": "💬 <b>आप अभी किसी चैट में नहीं हैं।</b>\n\n🔎 शुरू करने के लिए <b>अजनबी खोजें</b> दबाएँ।",
        "relay_error": "⚠️ <b>मैं वह संदेश भेज नहीं सका।</b>",
        "language_title": "🌐 <b>अपनी भाषा चुनें</b>\n\nबॉट में इस्तेमाल करने के लिए भाषा चुनें।",
        "language_saved": "✅ <b>भाषा अपडेट हो गई!</b>",
    },
    "es": {
        "find": "🔎 Buscar extraño",
        "language": "🌐 Idioma",
        "next": "⏭️ Siguiente",
        "stop": "🛑 Detener",
        "report": "🚨 Denunciar",
        "welcome": "👋 <b>Bienvenido a Anonymous Chat</b>\n\n🕵️ Habla anónimamente con personas al azar.\n🔒 Tu identidad permanece privada.\n🌍 Conoce gente de todo el mundo.\n\n🔎 ¡Pulsa <b>Buscar extraño</b> para empezar!",
        "already_chat": "💬 <b>Ya estás chateando con un desconocido.</b>",
        "already_search": "🔎 <b>Ya estás buscando...</b>",
        "found": "🎉 <b>¡Desconocido encontrado!</b>\n\n🔒 Ahora estás conectado de forma anónima.\n💬 ¡Saluda y empieza a chatear!\n\n🛡️ Mantén el anonimato y diviértete.",
        "searching": "🔎 <b>Buscando a alguien...</b>\n\n⏳ Espera mientras encontramos a alguien para ti.",
        "left": "❌ <b>El desconocido salió del chat.</b>\n\n💬 Puedes buscar a alguien nuevo.",
        "stopped": "🛑 <b>Chat detenido.</b>\n\n🔎 Pulsa <b>Buscar extraño</b> para empezar de nuevo.",
        "search_stopped": "🛑 <b>Búsqueda detenida.</b>\n\n🔎 Pulsa <b>Buscar extraño</b> para empezar de nuevo.",
        "not_chat": "ℹ️ No estás en un chat.",
        "report": "🚨 <b>Denuncia enviada.</b>\n\n🛑 El chat ha terminado.",
        "no_chat": "💬 <b>No estás en un chat.</b>\n\n🔎 Pulsa <b>Buscar extraño</b> para empezar.",
        "relay_error": "⚠️ <b>No pude enviar ese mensaje.</b>",
        "language_title": "🌐 <b>Elige tu idioma</b>\n\nSelecciona el idioma que quieres usar en el bot.",
        "language_saved": "✅ <b>¡Idioma actualizado!</b>",
    },
    "pt": {
        "find": "🔎 Encontrar Estranho",
        "language": "🌐 Idioma",
        "next": "⏭️ Próximo",
        "stop": "🛑 Parar",
        "report": "🚨 Denunciar",
        "welcome": "👋 <b>Bem-vindo ao Anonymous Chat</b>\n\n🕵️ Converse anonimamente com pessoas aleatórias.\n🔒 Sua identidade permanece privada.\n🌍 Conheça pessoas de qualquer lugar.\n\n🔎 Toque em <b>Encontrar Estranho</b> para começar!",
        "already_chat": "💬 <b>Você já está conversando com um estranho.</b>",
        "already_search": "🔎 <b>Você já está procurando...</b>",
        "found": "🎉 <b>Estranho encontrado!</b>\n\n🔒 Você está conectado anonimamente.\n💬 Diga olá e comece a conversar!\n\n🛡️ Mantenha o anonimato e divirta-se.",
        "searching": "🔎 <b>Procurando alguém...</b>\n\n⏳ Aguarde enquanto encontramos alguém para você.",
        "left": "❌ <b>O estranho saiu do chat.</b>\n\n💬 Você pode encontrar outra pessoa.",
        "stopped": "🛑 <b>Chat encerrado.</b>\n\n🔎 Toque em <b>Encontrar Estranho</b> para começar novamente.",
        "search_stopped": "🛑 <b>Busca encerrada.</b>\n\n🔎 Toque em <b>Encontrar Estranho</b> para começar novamente.",
        "not_chat": "ℹ️ Você não está em um chat.",
        "report": "🚨 <b>Denúncia enviada.</b>\n\n🛑 O chat foi encerrado.",
        "no_chat": "💬 <b>Você não está em um chat.</b>\n\n🔎 Toque em <b>Encontrar Estranho</b> para começar.",
        "relay_error": "⚠️ <b>Não consegui enviar essa mensagem.</b>",
        "language_title": "🌐 <b>Escolha seu idioma</b>\n\nSelecione o idioma que deseja usar no bot.",
        "language_saved": "✅ <b>Idioma atualizado!</b>",
    },
    "fr": {
        "find": "🔎 Trouver un inconnu",
        "language": "🌐 Langue",
        "next": "⏭️ Suivant",
        "stop": "🛑 Arrêter",
        "report": "🚨 Signaler",
        "welcome": "👋 <b>Bienvenue sur Anonymous Chat</b>\n\n🕵️ Discutez anonymement avec des personnes au hasard.\n🔒 Votre identité reste privée.\n🌍 Rencontrez des personnes du monde entier.\n\n🔎 Appuyez sur <b>Trouver un inconnu</b> pour commencer !",
        "already_chat": "💬 <b>Vous discutez déjà avec un inconnu.</b>",
        "already_search": "🔎 <b>Vous êtes déjà en recherche...</b>",
        "found": "🎉 <b>Inconnu trouvé !</b>\n\n🔒 Vous êtes maintenant connecté anonymement.\n💬 Dites bonjour et commencez à discuter !\n\n🛡️ Restez anonyme et amusez-vous.",
        "searching": "🔎 <b>Recherche d'un inconnu...</b>\n\n⏳ Veuillez patienter.",
        "left": "❌ <b>L'inconnu a quitté le chat.</b>\n\n💬 Vous pouvez chercher quelqu'un d'autre.",
        "stopped": "🛑 <b>Chat arrêté.</b>\n\n🔎 Appuyez sur <b>Trouver un inconnu</b> pour recommencer.",
        "search_stopped": "🛑 <b>Recherche arrêtée.</b>\n\n🔎 Appuyez sur <b>Trouver un inconnu</b> pour recommencer.",
        "not_chat": "ℹ️ Vous n'êtes actuellement dans aucun chat.",
        "report": "🚨 <b>Signalement envoyé.</b>\n\n🛑 Le chat a été terminé.",
        "no_chat": "💬 <b>Vous n'êtes actuellement dans aucun chat.</b>\n\n🔎 Appuyez sur <b>Trouver un inconnu</b> pour commencer.",
        "relay_error": "⚠️ <b>Je n'ai pas pu envoyer ce message.</b>",
        "language_title": "🌐 <b>Choisissez votre langue</b>\n\nSélectionnez la langue à utiliser dans le bot.",
        "language_saved": "✅ <b>Langue mise à jour !</b>",
    },
    "ar": {
        "find": "🔎 البحث عن شخص",
        "language": "🌐 اللغة",
        "next": "⏭️ التالي",
        "stop": "🛑 إيقاف",
        "report": "🚨 إبلاغ",
        "welcome": "👋 <b>مرحباً بك في الدردشة المجهولة</b>\n\n🕵️ تحدث بشكل مجهول مع أشخاص عشوائيين.\n🔒 هويتك تبقى خاصة.\n🌍 تعرّف على أشخاص من جميع أنحاء العالم.\n\n🔎 اضغط <b>البحث عن شخص</b> للبدء!",
        "already_chat": "💬 <b>أنت تتحدث بالفعل مع شخص.</b>",
        "already_search": "🔎 <b>أنت تبحث بالفعل...</b>",
        "found": "🎉 <b>تم العثور على شخص!</b>\n\n🔒 تم توصيلك بشكل مجهول.\n💬 قل مرحباً وابدأ الدردشة!\n\n🛡️ ابقَ مجهولاً واستمتع.",
        "searching": "🔎 <b>جارٍ البحث عن شخص...</b>\n\n⏳ يرجى الانتظار.",
        "left": "❌ <b>غادر الشخص الدردشة.</b>\n\n💬 يمكنك البحث عن شخص جديد.",
        "stopped": "🛑 <b>تم إيقاف الدردشة.</b>\n\n🔎 اضغط <b>البحث عن شخص</b> للبدء من جديد.",
        "search_stopped": "🛑 <b>تم إيقاف البحث.</b>\n\n🔎 اضغط <b>البحث عن شخص</b> للبدء من جديد.",
        "not_chat": "ℹ️ أنت لست في محادثة حالياً.",
        "report": "🚨 <b>تم إرسال البلاغ.</b>\n\n🛑 تم إنهاء الدردشة.",
        "no_chat": "💬 <b>أنت لست في محادثة حالياً.</b>\n\n🔎 اضغط <b>البحث عن شخص</b> للبدء.",
        "relay_error": "⚠️ <b>تعذر إرسال الرسالة.</b>",
        "language_title": "🌐 <b>اختر لغتك</b>\n\nاختر اللغة التي تريد استخدامها في البوت.",
        "language_saved": "✅ <b>تم تحديث اللغة!</b>",
    },
    "ru": {
        "find": "🔎 Найти собеседника",
        "language": "🌐 Язык",
        "next": "⏭️ Следующий",
        "stop": "🛑 Стоп",
        "report": "🚨 Пожаловаться",
        "welcome": "👋 <b>Добро пожаловать в Anonymous Chat</b>\n\n🕵️ Общайтесь анонимно со случайными людьми.\n🔒 Ваша личность останется приватной.\n🌍 Знакомьтесь с людьми со всего мира.\n\n🔎 Нажмите <b>Найти собеседника</b>, чтобы начать!",
        "already_chat": "💬 <b>Вы уже общаетесь с собеседником.</b>",
        "already_search": "🔎 <b>Вы уже ищете собеседника...</b>",
        "found": "🎉 <b>Собеседник найден!</b>\n\n🔒 Вы подключены анонимно.\n💬 Поздоровайтесь и начните общение!\n\n🛡️ Сохраняйте анонимность и общайтесь.",
        "searching": "🔎 <b>Ищем собеседника...</b>\n\n⏳ Пожалуйста, подождите.",
        "left": "❌ <b>Собеседник вышел из чата.</b>\n\n💬 Вы можете найти нового собеседника.",
        "stopped": "🛑 <b>Чат остановлен.</b>\n\n🔎 Нажмите <b>Найти собеседника</b>, чтобы начать снова.",
        "search_stopped": "🛑 <b>Поиск остановлен.</b>\n\n🔎 Нажмите <b>Найти собеседника</b>, чтобы начать снова.",
        "not_chat": "ℹ️ Вы сейчас не в чате.",
        "report": "🚨 <b>Жалоба отправлена.</b>\n\n🛑 Чат завершён.",
        "no_chat": "💬 <b>Вы сейчас не в чате.</b>\n\n🔎 Нажмите <b>Найти собеседника</b>, чтобы начать.",
        "relay_error": "⚠️ <b>Не удалось отправить сообщение.</b>",
        "language_title": "🌐 <b>Выберите язык</b>\n\nВыберите язык, который хотите использовать в боте.",
        "language_saved": "✅ <b>Язык обновлён!</b>",
    },
}

def lang(user_id):
    return user_languages.get(user_id, "en")

def t(user_id, key):
    return TEXT[lang(user_id)][key]

def main_keyboard(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(
        KeyboardButton(t(user_id, "find")),
        KeyboardButton(t(user_id, "language")),
    )
    return kb

def chat_keyboard(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add(
        KeyboardButton(t(user_id, "next")),
        KeyboardButton(t(user_id, "stop")),
        KeyboardButton(t(user_id, "report")),
    )
    return kb

def language_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for code, name in LANGUAGES.items():
        kb.add(KeyboardButton(name))
    return kb

async def send_main_menu(user_id):
    await bot.send_message(user_id, t(user_id, "welcome"), reply_markup=main_keyboard(user_id))

async def show_language_menu(user_id):
    await bot.send_message(user_id, t(user_id, "language_title"), reply_markup=language_keyboard())

def selected_language(text):
    for code, name in LANGUAGES.items():
        if text == name:
            return code
    return None

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
                t(partner_id, "left"),
                reply_markup=main_keyboard(partner_id),
            )
        except Exception as e:
            logging.error("Could not notify partner %s: %s", partner_id, e)
    return partner_id

async def find_match(user_id):
    if user_id in partners:
        await bot.send_message(user_id, t(user_id, "already_chat"), reply_markup=chat_keyboard(user_id))
        return
    if user_id in searching:
        await bot.send_message(user_id, t(user_id, "already_search"))
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

        await bot.send_message(user_id, t(user_id, "found"), reply_markup=chat_keyboard(user_id))
        await bot.send_message(partner_id, t(partner_id, "found"), reply_markup=chat_keyboard(partner_id))
        logging.info("MATCH: %s <-> %s", user_id, partner_id)
        return

    searching.add(user_id)
    waiting_users.append(user_id)
    await bot.send_message(user_id, t(user_id, "searching"), reply_markup=main_keyboard(user_id))
    logging.info("SEARCHING: %s | queue=%s", user_id, len(waiting_users))

@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in partners:
        await message.answer(t(user_id, "already_chat"), reply_markup=chat_keyboard(user_id))
        return
    if user_id in searching:
        await message.answer(t(user_id, "already_search"))
        return
    await send_main_menu(user_id)

@dp.message_handler(commands=["next"])
async def next_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in searching:
        await message.answer(t(user_id, "already_search"))
        return
    if user_id in partners:
        await end_chat(user_id, notify_partner=True)
        await message.answer("⏭️ " + t(user_id, "next"))
        await find_match(user_id)
        return
    await find_match(user_id)

@dp.message_handler(commands=["stop"])
async def stop_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in searching:
        await remove_from_queue(user_id)
        await message.answer(t(user_id, "search_stopped"), reply_markup=main_keyboard(user_id))
        return
    if user_id in partners:
        await end_chat(user_id, notify_partner=True)
        await message.answer(t(user_id, "stopped"), reply_markup=main_keyboard(user_id))
        return
    await message.answer(t(user_id, "not_chat"), reply_markup=main_keyboard(user_id))

@dp.message_handler(commands=["report"])
async def report_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in partners:
        await message.answer(t(user_id, "not_chat"))
        return
    partner_id = partners.get(user_id)
    logging.warning("REPORT: user %s reported user %s", user_id, partner_id)
    await end_chat(user_id, notify_partner=True)
    await message.answer(t(user_id, "report"), reply_markup=main_keyboard(user_id))

@dp.message_handler(content_types=types.ContentTypes.ANY)
async def relay_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text or ""

    chosen = selected_language(text)
    if chosen:
        user_languages[user_id] = chosen
        await message.answer(
            t(user_id, "language_saved"),
            reply_markup=main_keyboard(user_id) if user_id not in partners else chat_keyboard(user_id),
        )
        if user_id not in partners and user_id not in searching:
            await send_main_menu(user_id)
        return

    if text == t(user_id, "language"):
        await show_language_menu(user_id)
        return

    if text == t(user_id, "find"):
        await find_match(user_id)
        return

    if text == t(user_id, "next"):
        if user_id in partners:
            await end_chat(user_id, notify_partner=True)
            await message.answer("⏭️ " + t(user_id, "next"))
        elif user_id in searching:
            await message.answer(t(user_id, "already_search"))
            return
        else:
            await message.answer("🔎 " + t(user_id, "find"))
        await find_match(user_id)
        return

    if text == t(user_id, "stop"):
        if user_id in searching:
            await remove_from_queue(user_id)
        elif user_id in partners:
            await end_chat(user_id, notify_partner=True)
        await message.answer(t(user_id, "stopped"), reply_markup=main_keyboard(user_id))
        return

    if text == t(user_id, "report"):
        if user_id not in partners:
            await message.answer(t(user_id, "not_chat"), reply_markup=main_keyboard(user_id))
            return
        partner_id = partners.get(user_id)
        logging.warning("REPORT: user %s reported user %s", user_id, partner_id)
        await end_chat(user_id, notify_partner=True)
        await message.answer(t(user_id, "report"), reply_markup=main_keyboard(user_id))
        return

    if text.startswith("/"):
        return

    partner_id = partners.get(user_id)
    if not partner_id:
        await message.answer(t(user_id, "no_chat"), reply_markup=main_keyboard(user_id))
        return

    try:
        await bot.copy_message(
            chat_id=partner_id,
            from_chat_id=user_id,
            message_id=message.message_id,
        )
    except Exception as e:
        logging.error("Message relay failed: %s", e)
        await message.answer(t(user_id, "relay_error"))

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
