import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import os

# Lista de productos
ADS = [
    {
        "image": "producto1.jpg",
        "caption": "🔥 Producto 1 en oferta 🔥",
        "buttons": [
            InlineKeyboardButton("💲 Precio", url="https://tuweb.com/producto1"),
            InlineKeyboardButton("🛒 Comprar", url="https://tuweb.com/comprar1"),
            InlineKeyboardButton("📤 Compartir", url="https://tuweb.com/compartir1"),
        ],
    },
    {
        "image": "producto2.jpg",
        "caption": "🎉 Producto 2 exclusivo 🎉",
        "buttons": [
            InlineKeyboardButton("💲 Precio", url="https://tuweb.com/producto2"),
            InlineKeyboardButton("🛒 Comprar", url="https://tuweb.com/comprar2"),
            InlineKeyboardButton("📤 Compartir", url="https://tuweb.com/compartir2"),
        ],
    },
    {
        "image": "producto3.jpg",
        "caption": "🚀 Producto 3 con envío gratis 🚀",
        "buttons": [
            InlineKeyboardButton("💲 Precio", url="https://tuweb.com/producto3"),
            InlineKeyboardButton("🛒 Comprar", url="https://tuweb.com/comprar3"),
            InlineKeyboardButton("📤 Compartir", url="https://tuweb.com/compartir3"),
        ],
    },
    {
        "image": "producto4.jpg",
        "caption": "📦 Producto 4: última oportunidad 📦",
        "buttons": [
            InlineKeyboardButton("💲 Precio", url="https://tuweb.com/producto4"),
            InlineKeyboardButton("🛒 Comprar", url="https://tuweb.com/comprar4"),
            InlineKeyboardButton("📤 Compartir", url="https://tuweb.com/compartir4"),
        ],
    },
    # Se comenta el producto 5 porque la imagen no existe
    # {
    #     "image": "producto5.jpg",
    #     "caption": "🌟 Contrata nuestro servicio ahora 🌟",
    #     "buttons": [
    #         InlineKeyboardButton("💲 Contratar + Info", url="https://tuweb.com/contratar"),
    #         InlineKeyboardButton("📤 Compartir", url="https://tuweb.com/compartir5"),
    #     ],
    # },
]

async def send_ads(context: ContextTypes.DEFAULT_TYPE):
    """Envía anuncios aleatorios al grupo actual y programa el siguiente envío."""
    # Obtener la lista de chats donde está el bot
    bot_chats = await context.bot.get_updates()
    chat_ids = []
    
    # Extraer los IDs de chat de los grupos
    for update in bot_chats:
        if update.message and update.message.chat.type in ["group", "supergroup"]:
            if update.message.chat.id not in chat_ids:
                chat_ids.append(update.message.chat.id)
    
    # Si no hay grupos, usar el CHAT_ID de respaldo
    if not chat_ids:
        chat_id = os.getenv('CHAT_ID')
        if not chat_id:
            print("No se encontraron grupos y CHAT_ID no está definido en el archivo .env")
            return
        chat_ids = [chat_id]
    
    # Seleccionar anuncios aleatorios (máximo los disponibles)
    num_ads = min(4, len(ADS))  # Ajustado para usar solo los anuncios disponibles
    selected_ads = random.sample(ADS, num_ads)

    # Enviar anuncios a todos los grupos donde está el bot
    for chat_id in chat_ids:
        for ad in selected_ads:
            try:
                with open(ad["image"], "rb") as image:
                    markup = InlineKeyboardMarkup([ad["buttons"]])
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=image,
                        caption=ad["caption"],
                        reply_markup=markup
                    )
            except FileNotFoundError:
                print(f"Error: No se encontró la imagen {ad['image']}")
            except Exception as e:
                print(f"Error al enviar anuncio al chat {chat_id}: {e}")

    # Programar la próxima ejecución en 30-45 minutos
    wait_time = random.randint(100, 200)  # Entre 30 y 45 minutos 1800, 2700
    context.job_queue.run_once(send_ads, wait_time)