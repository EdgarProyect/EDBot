import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio

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
    {
        "image": "producto5.jpg",
        "caption": "🌟 Contratá nuestro servicio ahora 🌟",
        "buttons": [
            InlineKeyboardButton("💲 Contratar + Info", url="https://wa.me/5491161051718"),
            InlineKeyboardButton("📤 Compartir", url="https://edgarglienke.com.ar/bot"),
        ],
    },
]

# ✅ Función que se ejecuta indefinidamente para un grupo específico
async def send_ads(chat_id, bot):
    while True:
        try:
            num_ads = min(4, len(ADS))
            selected_ads = random.sample(ADS, num_ads)

            for ad in selected_ads:
                try:
                    with open(ad["image"], "rb") as image:
                        markup = InlineKeyboardMarkup([ad["buttons"]])
                        await bot.send_photo(
                            chat_id=chat_id,
                            photo=image,
                            caption=ad["caption"],
                            reply_markup=markup
                        )
                except FileNotFoundError:
                    print(f"⚠️ Imagen no encontrada: {ad['image']}")
                except Exception as e:
                    print(f"❌ Error al enviar anuncio a {chat_id}: {e}")

            # Espera 30 a 45 minutos antes de volver a publicar
            wait_time = random.randint(60, 120)
            await asyncio.sleep(wait_time)

        except Exception as e:
            print(f"❌ Error en el publicador de {chat_id}: {e}")
            await asyncio.sleep(60)  # Espera antes de intentar de nuevo
