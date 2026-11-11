import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Permite ejecutar este archivo directamente o como módulo desde la raíz.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.domotica import cliente_domotica as dom

load_dotenv(Path(__file__).with_name(".env"))

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_autorizado = os.getenv("TELEGRAM_CHAT_ID")

if not token or not chat_autorizado:
    print("Falta el token o el chat_id en .env.")
    raise SystemExit(1)

URL_BASE = f"https://api.telegram.org/bot{token}"

BOTON_ESTADO = "📋 Estado"
BOTON_VENTILADOR = "🌀 Ventilador"
BOTON_AYUDA = "❔ Ayuda"
BOTON_MANUAL = "✋ Manual"
BOTON_AUTOMATICO = "🌡️ Automático"
BOTON_VOLVER = "⬅️ Volver"
VELOCIDADES = {f"{velocidad} %": str(velocidad) for velocidad in (0, 30, 60, 100)}
MENU_PRINCIPAL = [[BOTON_ESTADO, BOTON_VENTILADOR], [BOTON_AYUDA]]
MENU_VENTILADOR = [[BOTON_MANUAL, BOTON_AUTOMATICO], list(VELOCIDADES), [BOTON_VOLVER]]


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


def enviar_mensaje(texto, teclado=None):
    contenido = {
        "chat_id": chat_autorizado,
        "text": texto
    }
    if teclado is not None:
        contenido["reply_markup"] = {"keyboard": teclado, "resize_keyboard": True}
    consultar_api("sendMessage", contenido)


def obtener_estado():
    try:
        return dom.texto_estado()
    except requests.RequestException:
        return "⚠️ No pude consultar el estado de Biboteca. Comprueba que la API esté en ejecución."


def responder_control(comando, argumentos):
    try:
        if comando == "/ventilador":
            return dom.comando_ventilador(*argumentos, requiere_manual=True)
        if argumentos:
            return f"⚠️ Usa {comando} sin argumentos."
        return dom.cambiar_modo_ventilador("manual" if comando == "/manual" else "auto")
    except requests.RequestException:
        return "⚠️ No pude confirmar la solicitud del ventilador. Comprueba que la API esté en ejecución."


def responder_mensaje(texto):
    texto = texto.strip().lower()
    if not texto:
        return

    comando, *argumentos = texto.split()
    if texto == BOTON_ESTADO.lower() or texto == "/estado":
        enviar_mensaje(obtener_estado())
    elif texto == BOTON_VENTILADOR.lower():
        estado = responder_control("/ventilador", [])
        enviar_mensaje(
            f"{estado}\n\nToca Manual y elige una velocidad, o toca Automático para que el sistema la ajuste según la temperatura.",
            MENU_VENTILADOR,
        )
    elif texto == BOTON_MANUAL.lower():
        enviar_mensaje(responder_control("/manual", []))
    elif texto == BOTON_AUTOMATICO.lower():
        enviar_mensaje(responder_control("/automatico", []))
    elif texto in VELOCIDADES:
        enviar_mensaje(responder_control("/ventilador", [VELOCIDADES[texto]]))
    elif comando in ("/manual", "/automatico", "/ventilador"):
        enviar_mensaje(responder_control(comando, argumentos))
    elif texto == "/start" or texto == BOTON_VOLVER.lower():
        enviar_mensaje("📚 Biboteca\nConsulta el estado de la biblioteca o ajusta el ventilador.", MENU_PRINCIPAL)
    elif texto in ("/ayuda", BOTON_AYUDA.lower()):
        enviar_mensaje(
            "📋 Estado muestra las lecturas, la puerta y la alarma.\n"
            "🌀 Ventilador permite cambiar el modo y elegir una velocidad. "
            "Para usar un porcentaje que no aparece en los botones, toca Manual y escribe, por ejemplo, /ventilador 45.",
            MENU_PRINCIPAL,
        )
    elif texto.startswith("/"):
        enviar_mensaje("Ese comando no está disponible. Elige una opción del menú o toca Ayuda.", MENU_PRINCIPAL)


def iniciar_bot():
    siguiente_id = None
    print("Biboteca está escuchando. Escribe /start en Telegram para abrir el menú.")
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

                responder_mensaje(mensaje.get("text", ""))

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
