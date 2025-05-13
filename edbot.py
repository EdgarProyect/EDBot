import logging 
import os 
import asyncio 
import datetime
import time
import re
from collections import defaultdict, Counter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
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
 
# Habilitar el registro de errores con nivel DEBUG para más información 
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG) 
logger = logging.getLogger(__name__) 

# Configuración de moderación
BANNED_WORDS = ["puto", "puta", "palabrota1", "palabrota2", "spam", "scam"]
GREETING_WORDS = ["hola", "buenas", "saludos", "hey"]
THANKS_WORDS = ["gracias", "thanks", "thx", "agradecido"]
SPAM_LINKS = ["bit.ly", "tinyurl", "acortador.com", "spam.com"]
WARNING_THRESHOLD = 3  # Número de advertencias antes de silenciar
MUTE_DURATION = 60 * 10  # 10 minutos en segundos
BAN_THRESHOLD = 3  # Número de advertencias antes de banear

# Diccionarios para seguimiento de usuarios
user_warnings = defaultdict(int)  # {user_id: número de advertencias}
user_messages = defaultdict(list)  # {user_id: [timestamp1, timestamp2, ...]}
message_counter = Counter()  # Contador para mensajes repetidos

# Función para manejar cuando un usuario acepta las políticas 
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    query = update.callback_query 
    await query.answer() 
     
    # Verificar si es una aceptación de política 
    if query.data.startswith("accept_policy_"): 
        user_id = query.data.split("_")[2] 
        user = query.from_user 
         
        if str(user.id) == user_id: 
            await query.edit_message_text( 
                text=f"¡Gracias {user.first_name}! Has aceptado las políticas del grupo. Ahora puedes disfrutar de todas las funcionalidades.", 
                reply_markup=None 
            ) 
        else: 
            await query.edit_message_text( 
                text="Este botón es solo para el usuario que acaba de unirse al grupo.", 
                reply_markup=query.message.reply_markup 
            ) 

# Función para enviar anuncios repetitivos 
async def schedule_ads(context: ContextTypes.DEFAULT_TYPE): 
    await send_ads(context.bot) 
    context.job_queue.run_once(schedule_ads, 1800)  # Repetir cada 30 min 
 
# Función para iniciar el bot 
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
    # ... existing code ...
 
# Función para manejar nuevos miembros en el grupo 
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
             
            await update.message.reply_text("📲 ¡Sígueme en mis redes sociales y acepta nuestras políticas!", reply_markup=markup) 
    # ... existing code ...

# Función para detectar y moderar mensajes
async def moderate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat_id
    text = message.text.lower()
    
    # 1. Detectar palabras clave y reaccionar
    
    # Saludos
    if any(word in text for word in GREETING_WORDS):
        await message.reply_text(f"¡Hola {message.from_user.first_name}! 👋")
        return
    
    # Agradecimientos
    if any(word in text for word in THANKS_WORDS):
        await message.reply_text(f"¡De nada {message.from_user.first_name}! 😊")
        return
    
    # 2. Detectar insultos y spam
    
    # Palabras prohibidas
    if any(word in text for word in BANNED_WORDS):
        await message.delete()
        warning = f"⚠️ {message.from_user.mention_markdown()}, por favor evita usar lenguaje inapropiado."
        warning_msg = await context.bot.send_message(chat_id=chat_id, text=warning, parse_mode="Markdown")
        
        # Incrementar advertencias
        user_warnings[user_id] += 1
        
        # Eliminar mensaje de advertencia después de 30 segundos
        await asyncio.sleep(30)
        await warning_msg.delete()
        
        # Verificar si se debe silenciar o banear
        await check_penalties(update, context, user_id)
        return
    
    # Enlaces de spam
    if any(link in text for link in SPAM_LINKS):
        await message.delete()
        warning = f"⚠️ {message.from_user.mention_markdown()}, no se permiten enlaces sospechosos."
        warning_msg = await context.bot.send_message(chat_id=chat_id, text=warning, parse_mode="Markdown")
        
        # Incrementar advertencias
        user_warnings[user_id] += 1
        
        # Eliminar mensaje de advertencia después de 30 segundos
        await asyncio.sleep(30)
        await warning_msg.delete()
        
        # Verificar si se debe silenciar o banear
        await check_penalties(update, context, user_id)
        return
    
    # 3. Detectar flood (mensajes repetidos rápidamente)
    current_time = time.time()
    user_messages[user_id].append(current_time)
    
    # Limpiar mensajes antiguos (más de 60 segundos)
    user_messages[user_id] = [t for t in user_messages[user_id] if current_time - t < 60]
    
    # Si hay más de 5 mensajes en menos de 60 segundos
    if len(user_messages[user_id]) > 5:
        await message.delete()
        warning = f"⚠️ {message.from_user.mention_markdown()}, por favor no envíes mensajes tan rápido (flood)."
        warning_msg = await context.bot.send_message(chat_id=chat_id, text=warning, parse_mode="Markdown")
        
        # Incrementar advertencias
        user_warnings[user_id] += 1
        
        # Eliminar mensaje de advertencia después de 30 segundos
        await asyncio.sleep(30)
        await warning_msg.delete()
        
        # Verificar si se debe silenciar o banear
        await check_penalties(update, context, user_id)
        return
    
    # 4. Detectar mensajes repetidos
    # Contar mensajes idénticos en los últimos 2 minutos
    message_counter[text] += 1
    
    # Si el mismo mensaje se repite más de 3 veces
    if message_counter[text] > 3:
        await message.delete()
        warning = f"⚠️ {message.from_user.mention_markdown()}, por favor no repitas el mismo mensaje."
        warning_msg = await context.bot.send_message(chat_id=chat_id, text=warning, parse_mode="Markdown")
        
        # Incrementar advertencias
        user_warnings[user_id] += 1
        
        # Eliminar mensaje de advertencia después de 30 segundos
        await asyncio.sleep(30)
        await warning_msg.delete()
        
        # Verificar si se debe silenciar o banear
        await check_penalties(update, context, user_id)
        return

# Función para aplicar penalizaciones según el número de advertencias
async def check_penalties(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    chat_id = update.message.chat_id
    
    # Si el usuario alcanzó el umbral de baneo
    if user_warnings[user_id] >= BAN_THRESHOLD:
        try:
            # Banear al usuario
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            
            ban_message = f"🚫 Usuario baneado por múltiples infracciones."
            await context.bot.send_message(chat_id=chat_id, text=ban_message)
            
            # Resetear advertencias
            user_warnings[user_id] = 0
            
        except BadRequest as e:
            logger.error(f"No se pudo banear al usuario: {e}")
    
    # Si el usuario alcanzó el umbral de silencio
    elif user_warnings[user_id] >= WARNING_THRESHOLD:
        try:
            # Silenciar al usuario
            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            )
            
            until_date = int(time.time() + MUTE_DURATION)
            await context.bot.restrict_chat_member(
                chat_id=chat_id, 
                user_id=user_id,
                permissions=permissions,
                until_date=until_date
            )
            
            mute_message = f"🔇 Usuario silenciado por {MUTE_DURATION//60} minutos debido a múltiples advertencias."
            await context.bot.send_message(chat_id=chat_id, text=mute_message)
            
        except BadRequest as e:
            logger.error(f"No se pudo silenciar al usuario: {e}")

# Comando para limpiar advertencias de un usuario (solo para administradores)
async def clear_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verificar si el usuario es administrador
    user = update.effective_user
    chat = update.effective_chat
    
    if not chat.type in ['group', 'supergroup']:
        await update.message.reply_text("Este comando solo funciona en grupos.")
        return
    
    # Verificar si el usuario es administrador
    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in ['administrator', 'creator']:
        await update.message.reply_text("Solo los administradores pueden usar este comando.")
        return
    
    # Verificar si se proporcionó un usuario
    if not context.args:
        await update.message.reply_text("Uso: /clearwarnings @usuario o ID_usuario")
        return
    
    # Obtener el ID del usuario
    target = context.args[0]
    if target.startswith('@'):
        # Buscar por nombre de usuario
        try:
            chat_member = await context.bot.get_chat_member(chat.id, target)
            target_id = chat_member.user.id
        except BadRequest:
            await update.message.reply_text(f"No se encontró al usuario {target} en este grupo.")
            return
    else:
        # Usar ID directamente
        try:
            target_id = int(target)
        except ValueError:
            await update.message.reply_text("Por favor proporciona un ID de usuario válido o @nombre_usuario.")
            return
    
    # Limpiar advertencias
    if target_id in user_warnings:
        old_warnings = user_warnings[target_id]
        user_warnings[target_id] = 0
        await update.message.reply_text(f"Se han eliminado {old_warnings} advertencias del usuario.")
    else:
        await update.message.reply_text("Este usuario no tiene advertencias.")

# Comando para ver advertencias de un usuario
async def check_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verificar si el usuario es administrador
    user = update.effective_user
    chat = update.effective_chat
    
    if not chat.type in ['group', 'supergroup']:
        await update.message.reply_text("Este comando solo funciona en grupos.")
        return
    
    # Verificar si se proporcionó un usuario
    if not context.args:
        # Mostrar advertencias del usuario que ejecuta el comando
        warnings = user_warnings.get(user.id, 0)
        await update.message.reply_text(f"Tienes {warnings} advertencia(s).")
        return
    
    # Verificar si el usuario es administrador
    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in ['administrator', 'creator']:
        await update.message.reply_text("Solo los administradores pueden ver advertencias de otros usuarios.")
        return
    
    # Obtener el ID del usuario
    target = context.args[0]
    if target.startswith('@'):
        # Buscar por nombre de usuario
        try:
            chat_member = await context.bot.get_chat_member(chat.id, target)
            target_id = chat_member.user.id
            target_name = chat_member.user.first_name
        except BadRequest:
            await update.message.reply_text(f"No se encontró al usuario {target} en este grupo.")
            return
    else:
        # Usar ID directamente
        try:
            target_id = int(target)
            try:
                chat_member = await context.bot.get_chat_member(chat.id, target_id)
                target_name = chat_member.user.first_name
            except BadRequest:
                target_name = f"Usuario {target_id}"
        except ValueError:
            await update.message.reply_text("Por favor proporciona un ID de usuario válido o @nombre_usuario.")
            return
    
    # Mostrar advertencias
    warnings = user_warnings.get(target_id, 0)
    await update.message.reply_text(f"{target_name} tiene {warnings} advertencia(s).")

# Tarea periódica para limpiar contadores de mensajes antiguos
async def clean_message_counters(context: ContextTypes.DEFAULT_TYPE):
    global message_counter
    # Reiniciar el contador cada 2 minutos
    message_counter = Counter()
    
    # Programar la próxima limpieza
    context.job_queue.run_once(clean_message_counters, 120)  # 2 minutos

# Función para inicializar tareas después de iniciar el bot 
async def post_init(application: Application): 
    application.job_queue.run_once(schedule_ads, when=5)  # Iniciar en 5 segundos
    application.job_queue.run_once(clean_message_counters, when=1)  # Iniciar limpieza de contadores
 
# Configuración del bot 
async def main(): 
    try: 
        logger.info("Iniciando el bot...") 
        # Aumentar los tiempos de espera y configurar opciones adicionales 
        application = ( 
            Application.builder() 
            .token(TOKEN) 
            .post_init(post_init) 
            .connect_timeout(30.0)  # Aumentar tiempo de espera de conexión a 30 segundos 
            .read_timeout(30.0)     # Aumentar tiempo de espera de lectura a 30 segundos 
            .write_timeout(30.0)    # Aumentar tiempo de espera de escritura a 30 segundos 
            .pool_timeout(30.0)     # Aumentar tiempo de espera del pool a 30 segundos 
            .build() 
        ) 
 
        # Agregar manejadores básicos
        application.add_handler(CommandHandler("start", start)) 
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member)) 
        application.add_handler(CallbackQueryHandler(button_callback)) 
        
        # Agregar manejadores de moderación
        application.add_handler(CommandHandler("clearwarnings", clear_warnings))
        application.add_handler(CommandHandler("warnings", check_warnings))
        
        # Manejador para moderar todos los mensajes (debe ir al final para procesar después de los comandos)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate_message))
 
        logger.info("Bot en línea y esperando comandos...") 
        logger.info(f"Usando token: {TOKEN[:5]}...{TOKEN[-5:]} (parcialmente oculto por seguridad)") 
        logger.info(f"Chat ID configurado: {CHAT_ID}") 
         
        # Método correcto para iniciar el bot en versiones recientes 
        await application.initialize() 
        logger.debug("Inicialización completada") 
         
        await application.start() 
        logger.debug("Aplicación iniciada") 
         
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True) 
        logger.debug("Polling iniciado") 
         
        # Mantener el bot ejecutándose hasta que se detenga manualmente 
        try: 
            # Usar un evento que nunca se completa para mantener el bot en ejecución 
            stop_signal = asyncio.Event() 
            await stop_signal.wait() 
        except asyncio.CancelledError: 
            pass 
             
    except Exception as e: 
        logger.error(f"Error: {e}", exc_info=True)  # Agregar exc_info para obtener el traceback completo 
    finally: 
        # Solo intentar detener si el bot está en ejecución 
        if 'application' in locals() and hasattr(application, "is_running") and application.is_running(): 
            await application.stop() 
 
if __name__ == '__main__': 
    asyncio.run(main())