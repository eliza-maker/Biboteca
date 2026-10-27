import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))
token = os.getenv("TELEGRAM_BOT_TOKEN")

if not token:
    print("Falta TELEGRAM_BOT_TOKEN en .env.")
    raise SystemExit(1)

url = f"https://api.telegram.org/bot{token}/getUpdates"

try:
    respuesta = requests.get(url, timeout=15)
    datos = respuesta.json()

    if not datos.get("ok"):
        print(f"Telegram rechazó la consulta. Código: {respuesta.status_code}")
    else:
        encontrado = False

        for actualizacion in datos["result"]:
            mensaje = actualizacion.get("message", {})
            chat = mensaje.get("chat", {})

            if chat.get("type") == "private":
                encontrado = True
                print("Mensaje:", mensaje.get("text", "(sin texto)"))
                print("CHAT_ID:", chat["id"])
                print()

        if not encontrado:
            print("No hay mensajes privados pendientes.")
            print("Envía otro mensaje al bot y vuelve a ejecutar.")

except requests.RequestException:
    print("No se pudo conectar con Telegram. Revisa tu conexión.")
except ValueError:
    print("La respuesta recibida no tiene el formato esperado.")