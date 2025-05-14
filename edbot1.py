import logging
import os
import asyncio
import nest_asyncio
nest_asyncio.apply()
import time
from collections import defaultdict, Counter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler, ChatMemberHandler
from telegram.error import BadRequest
from dotenv import load_dotenv
from ads import send_ads

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv('TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

if not TOKEN or not CHAT_ID:
    print("El token o CHAT_ID no está definido en el archivo .env")
    exit(1)

# Configurar logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configuración de moderación
BANNED_WORDS = ["puto", "puta", "palabrota1", "palabrota2", "spam", "scam"]
GREETING_WORDS = ["hola", "buenas", "saludos", "hey"]
THANKS_WORDS = ["gracias", "thanks", "thx", "agradecido"]
SPAM_LINKS = ["bit.ly", "tinyurl", "acortador.com", "spam.com"]
WARNING_THRESHOLD = 3
MUTE_DURATION = 60 * 10  # 10 minutos
BAN_THRESHOLD = 5

# Seguimiento de usuarios
user_warnings = defaultdict(int)
user_messages = defaultdict(list)
message_counter = Counter()

# Botón de aceptación de políticas
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("accept_policy_"):
        user_id = query.data.split("_")[2]
        user = query.from_user

        if str(user.id) == user_id:
            await query.edit_message_text(
                text=f"¡Gracias {user.first_name}! Has aceptado las políticas del grupo. Ahora puedes disfrutar de todas las funcionalidades."
            )
        else:
            await query.edit_message_text(
                text="Este botón es solo para el usuario que acaba de unirse al grupo.",
                reply_markup=query.message.reply_markup
            )

# Anuncios cada 30 min
async def schedule_ads(context: ContextTypes.DEFAULT_TYPE):
    await send_ads(context.bot)
    context.job_queue.run_once(schedule_ads, 1800)

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logo_path = "logo.png"
    with open(logo_path, "rb") as logo:
        await update.message.reply_photo(logo, caption="🌟 ¡Bienvenido a mi bot! 🌟")

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📘 Facebook", url="https://facebook.com/tu_pagina"),
            InlineKeyboardButton("🐦 Twitter", url="https://twitter.com/tu_perfil"),
            InlineKeyboardButton("📸 Instagram", url="https://instagram.com/tu_perfil"),
            InlineKeyboardButton("🎥 YouTube", url="https://youtube.com/tu_canal")
        ],
        [
            InlineKeyboardButton("🌐 Visita mi web", url="https://edgarglienke.com.ar")
        ]
    ])

    await update.message.reply_text("📲 ¡Sígueme en mis redes sociales!", reply_markup=markup)

# Nuevo miembro
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            username = member.username or "Invitado"
            welcome_message = f"¡Hola {username}! Bienvenido al grupo. 🎉\n\nPor favor, lee y acepta nuestras políticas del grupo para continuar."

            logo_path = "logo.png"
            with open(logo_path, "rb") as logo:
                await update.message.reply_photo(logo, caption=welcome_message)

            markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📘 Facebook", url="https://facebook.com/tu_pagina"),
                    InlineKeyboardButton("🐦 Twitter", url="https://twitter.com/tu_perfil")
                ],
                [
                    InlineKeyboardButton("📸 Instagram", url="https://instagram.com/tu_perfil"),
                    InlineKeyboardButton("🎥 YouTube", url="https://youtube.com/tu_canal")
                ],
                [
                    InlineKeyboardButton("🌐 Visita mi web", url="https://edgarglienke.com.ar")
                ],
                [
                    InlineKeyboardButton("✅ ACEPTO LAS POLÍTICAS DEL GRUPO", callback_data=f"accept_policy_{member.id}")
                ]
            ])

            await update.message.reply_text("📲 ¡Sígueme en redes y acepta las políticas!", reply_markup=markup)

# Moderación de mensajes
async def moderate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat_id
    text = message.text.lower()

    if any(word in text for word in GREETING_WORDS):
        await message.reply_text(f"¡Hola {message.from_user.first_name}! 👋")
        return

    if any(word in text for word in THANKS_WORDS):
        await message.reply_text(f"¡De nada {message.from_user.first_name}! 😊")
        return

    if any(word in text for word in BANNED_WORDS):
        await message.delete()
        warning = f"⚠️ {message.from_user.mention_markdown()}, por favor evita usar lenguaje inapropiado."
        warning_msg = await context.bot.send_message(chat_id, text=warning, parse_mode="Markdown")
        user_warnings[user_id] += 1
        await asyncio.sleep(30)
        await warning_msg.delete()
        await check_penalties(update, context, user_id)
        return

    if any(link in text for link in SPAM_LINKS):
        await message.delete()
        warning = f"⚠️ {message.from_user.mention_markdown()}, no se permiten enlaces sospechosos."
        warning_msg = await context.bot.send_message(chat_id, text=warning, parse_mode="Markdown")
        user_warnings[user_id] += 1
        await asyncio.sleep(30)
        await warning_msg.delete()
        await check_penalties(update, context, user_id)
        return

    now = time.time()
    user_messages[user_id].append(now)
    user_messages[user_id] = [t for t in user_messages[user_id] if now - t < 60]

    if len(user_messages[user_id]) > 5:
        await message.delete()
        warning = f"⚠️ {message.from_user.mention_markdown()}, estás enviando demasiados mensajes."
        warning_msg = await context.bot.send_message(chat_id, text=warning, parse_mode="Markdown")
        user_warnings[user_id] += 1
        await asyncio.sleep(30)
        await warning_msg.delete()
        await check_penalties(update, context, user_id)
        return

    message_counter[text] += 1
    if message_counter[text] > 3:
        await message.delete()
        warning = f"⚠️ {message.from_user.mention_markdown()}, no repitas el mismo mensaje."
        warning_msg = await context.bot.send_message(chat_id, text=warning, parse_mode="Markdown")
        user_warnings[user_id] += 1
        await asyncio.sleep(30)
        await warning_msg.delete()
        await check_penalties(update, context, user_id)

# Penalizaciones
async def check_penalties(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    chat_id = update.message.chat_id

    if user_warnings[user_id] >= BAN_THRESHOLD:
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await context.bot.send_message(chat_id, text="🚫 Usuario baneado por múltiples infracciones.")
            user_warnings[user_id] = 0
        except BadRequest as e:
            logger.error(f"No se pudo banear al usuario: {e}")

    elif user_warnings[user_id] >= WARNING_THRESHOLD:
        try:
            until = int(time.time()) + MUTE_DURATION
            permissions = ChatPermissions(can_send_messages=False)
            await context.bot.restrict_chat_member(chat_id, user_id, permissions, until_date=until)
            await context.bot.send_message(chat_id, text="🔇 Usuario silenciado por comportamiento inapropiado.")
        except BadRequest as e:
            logger.error(f"No se pudo silenciar al usuario: {e}")

# Al ser añadido a un grupo
async def bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if result.new_chat_member.status in ["member", "administrator"]:
        chat_title = result.chat.title or "este grupo"
        try:
            logo_path = "logo.png"
            with open(logo_path, "rb") as logo:
                await context.bot.send_photo(
                    chat_id=result.chat.id,
                    photo=logo,
                    caption=f"🤖 ¡Gracias por añadirme a *{chat_title}*! Estoy listo para moderar, dar la bienvenida y más. Usa /start para configurar.",
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Error enviando mensaje de bienvenida al grupo: {e}")

# Lanzar bot
async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate_message))
    app.add_handler(ChatMemberHandler(bot_added_to_group, chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER))

    app.job_queue.run_once(schedule_ads, 5)

    logger.info("Bot iniciado")
    await app.run_polling()

# Punto de entrada
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        pass
