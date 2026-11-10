import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Leer nuestras credenciales.
load_dotenv(Path(__file__).with_name(".env"))

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

if not token or not chat_id:
    print("Falta el token o el chat_id en .env.")
    raise SystemExit(1)

# Dirección de la API para enviar mensajes.
url = f"https://api.telegram.org/bot{token}/sendMessage"

# Cuerpo del mensaje: destinatario y texto.
mensaje = {
    "chat_id": chat_id,
    "text": "¡Hola! Soy Biboteca 📚. Este mensaje fue enviado desde Python."
}

try:
    respuesta = requests.post(url, json=mensaje, timeout=15)
    datos = respuesta.json()

    if datos.get("ok"):
        print("¡Mensaje enviado! Revisa Telegram.")
    else:
        print(f"Telegram rechazó el envío. Código: {respuesta.status_code}")
        print("Revisa el token, el chat_id y que hayas iniciado el bot.")

except requests.RequestException:
    print("No se pudo confirmar el envío. Revisa Telegram y tu conexión.")
except ValueError:
    print("La respuesta recibida no tiene el formato esperado.")