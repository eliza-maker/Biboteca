import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_autorizado = os.getenv("TELEGRAM_CHAT_ID")

if not token or not chat_autorizado:
    print("Falta el token o el chat_id en .env.")
    raise SystemExit(1)

URL_BASE = f"https://api.telegram.org/bot{token}"


def consultar_api(metodo, contenido):
    respuesta = requests.post(
        f"{URL_BASE}/{metodo}",
        json=contenido,
        timeout=40
    )
    datos = respuesta.json()

    if not datos.get("ok"):
        # No mostramos la URL porque contiene el token.
        raise RuntimeError(
            f"Telegram rechazó la solicitud: HTTP {respuesta.status_code}"
        )

    return datos["result"]


def enviar_mensaje(texto):
    consultar_api("sendMessage", {
        "chat_id": chat_autorizado,
        "text": texto
    })


def obtener_estado():
    # Datos de prueba: todavía no vienen de sensores.
    return (
        "📚 Estado de Biboteca\n"
        "🧪 DATOS SIMULADOS\n\n"
        "Temperatura: 24 °C\n"
        "Humedad: 55 %\n"
        "Iluminación: suficiente\n"
        "Lámpara: apagada\n"
        "Ventilador: apagado"
    )


def iniciar_bot():
    siguiente_id = None
    print("Biboteca está escuchando. Escribe /estado en Telegram.")
    print("Para detener el programa, presiona Ctrl + C.")

    while True:
        try:
            actualizaciones = consultar_api("getUpdates", {
                "offset": siguiente_id,
                "timeout": 30,
                "allowed_updates": ["message"]
            })

            for actualizacion in actualizaciones:
                # Evitar procesar nuevamente este mensaje.
                siguiente_id = actualizacion["update_id"] + 1

                mensaje = actualizacion.get("message", {})
                chat_id = str(mensaje.get("chat", {}).get("id", ""))

                # Por ahora, solo responder a tu conversación.
                if chat_id != chat_autorizado:
                    continue

                texto = mensaje.get("text", "").strip().lower()

                if texto == "/estado":
                    enviar_mensaje(obtener_estado())
                elif texto in ("/start", "/ayuda"):
                    enviar_mensaje(
                        "¡Hola! Soy Biboteca 📚.\n"
                        "Escribe /estado para consultar la biblioteca."
                    )

        except requests.RequestException:
            print("Problema de conexión. Reintentando en 5 segundos...")
            time.sleep(5)
        except ValueError:
            print("Respuesta inesperada. Reintentando en 5 segundos...")
            time.sleep(5)
        except RuntimeError as error:
            print(error)
            break


if __name__ == "__main__":
    try:
        iniciar_bot()
    except KeyboardInterrupt:
        print("\nBiboteca se detuvo.")