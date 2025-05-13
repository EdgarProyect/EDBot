import pywhatkit as kit
from time import sleep

# Función para enviar la imagen con mensaje
def enviar_imagen(numero, ruta_imagen, mensaje):
    kit.sendwhats_image(numero, ruta_imagen, mensaje)
    sleep(5)

# Función para enviar un mensaje con enlaces (en lugar de botones)
def enviar_mensaje(numero, mensaje):
    kit.sendwhatmsg_instantly(numero, mensaje)
    sleep(5)

def main():
    numero = "+5491161051718"
    ruta_imagen = "producto1.jpg"
    mensaje_imagen = "🔥 Producto 1 en oferta 🔥"

    # Enlaces como texto en el mensaje
    mensaje_texto = (
        "Aquí están tus opciones:\n"
        "💲 Precio: https://tuweb.com/producto1\n"
        "🛒 Comprar: https://tuweb.com/comprar1\n"
        "📤 Compartir: https://tuweb.com/compartir1"
    )

    enviar_imagen(numero, ruta_imagen, mensaje_imagen)
    enviar_mensaje(numero, mensaje_texto)

if __name__ == "__main__":
    main()
