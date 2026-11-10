"""Comandos de Telegram para la domótica (python-telegram-bot v20+).

En tu bot.py:
    import handlers_domotica
    handlers_domotica.registrar(application)

Si usas otra librería (pyTelegramBotAPI, aiogram...) llama igual a las funciones de
cliente_domotica: cada una devuelve el texto que debes enviar como respuesta.
"""
import asyncio

from telegram.ext import CommandHandler

import cliente_domotica as dom


def _cmd(funcion):
    async def handler(update, context):
        try:
            # requests es bloqueante: se ejecuta en un hilo para no frenar al bot
            texto = await asyncio.to_thread(funcion, *context.args)
        except Exception:
            texto = "⚠️ No pude comunicarme con el sistema de domótica."
        await update.message.reply_text(texto)
    return handler


def registrar(application):
    comandos = {
        "estado": dom.texto_estado,
        "temperatura": dom.texto_temperatura,
        "humedad": dom.texto_humedad,
        "puerta": dom.texto_puerta,
        "ventilador": dom.comando_ventilador,
        "alarma": dom.comando_alarma,
    }
    for nombre, funcion in comandos.items():
        application.add_handler(CommandHandler(nombre, _cmd(funcion)))
