import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def enviar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Distribución de botones en dos filas
    buttons = [
        [InlineKeyboardButton("💲 Precio", url="https://tuweb.com/producto1"),
         InlineKeyboardButton("🛒 Comprar", url="https://tuweb.com/comprar1")],
        [InlineKeyboardButton("📤 Compartir", url="https://tuweb.com/compartir1")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo="producto1.jpg", caption="🔥 Producto 1 en oferta 🔥", reply_markup=keyboard)

def main() -> None:
    application = ApplicationBuilder().token("7916605053:AAEQ4IcSRbHCeKaB16-qcLXdwzFBbUuQ5bc").build()

    start_handler = CommandHandler("start", enviar_mensaje)
    application.add_handler(start_handler)

    application.run_polling()

if __name__ == "__main__":
    main()