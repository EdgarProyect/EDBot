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
    # Llamamos a la función que envía los anuncios
    await send_ads(context.bot)
    
    # Programamos la ejecución del anuncio cada 30 minutos
    context.job_queue.run_repeating(schedule_ads, interval=90, first=0)


# Configurar el logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logo_path = "logo.png"
        with open(logo_path, "rb") as logo:
            await update.message.reply_photo(logo, caption="🌟 ¡Bienvenido al Grupo, {}! 🌟".format(update.message.from_user.first_name))

        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🌍 Facebook", url="https://facebook.com/tu_pagina"),
                InlineKeyboardButton("🐦 Twitter", url="https://twitter.com/tu_perfil"),
                InlineKeyboardButton("📸 Instagram", url="https://instagram.com/tu_perfil"),
                InlineKeyboardButton("🎥 YouTube", url="https://youtube.com/tu_canal")
            ],
            [
                InlineKeyboardButton("💻 Visita mi Web", url="https://edgarglienke.com.ar"),
                InlineKeyboardButton("📱 Contacto Directo", url="https://wa.me/5491161051718")
            ]
        ])

        await update.message.reply_text(
            "📲 ¡Sígueme en mis redes sociales y mantente conectado!",
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error al procesar /start: {e}")
        await update.message.reply_text("⚠️ Hubo un error al intentar enviarte la información. Por favor, inténtalo más tarde.")

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

# ... (el código anterior se mantiene igual hasta la línea que dice "# Función para enviar anuncios al grupo")

# Función para enviar anuncios al grupo
async def send_ads(bot):
    try:
        ad_message = "📢 Anuncio automático: No olvides visitar nuestra web oficial 👉 https://edgarglienke.com.ar y seguirnos en redes sociales."
        await bot.send_message(chat_id=CHAT_ID, text=ad_message)
    except Exception as e:
        logger.error(f"Error al enviar anuncio automático: {e}")

# Función principal
async def main():
    app = Application.builder().token(TOKEN).build()

    # Handlers de comandos y eventos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(ChatMemberHandler(bot_added_to_group, chat_member_types=["my_chat_member"]))

    # Iniciar anuncios programados
    app.job_queue.run_repeating(schedule_ads, interval=1800, first=10)  # cada 30 minutos

    logger.info("🤖 Bot iniciado correctamente.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())


    try:
        asyncio.get_running_loop().create_task(main())
    except RuntimeError:
        asyncio.run(main())   
# ... [todo tu código anterior sin cambios] ...

# ----------- AL FINAL DEL ARCHIVO ----------------

# MAIN
async def main():
    application = Application.builder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(ChatMemberHandler(bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER))

    # Tarea programada para anuncios cada 90 segundos
    application.job_queue.run_repeating(schedule_ads, interval=90, first=5)

    # Iniciar el bot
    logger.info("🚀 Bot iniciado correctamente")
    await application.run_polling()

# Ejecutar si es script principal
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
 
