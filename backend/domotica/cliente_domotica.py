"""Funciones para que el bot (o cualquier otro programa) use la API de domótica.

Cada variable y cada actuador tiene su función de lectura/escritura (devuelven datos) y su
función texto_*/comando_* (devuelven el mensaje listo para enviar por Telegram).
"""
import requests

BASE = "http://127.0.0.1:5000/api"
TIMEOUT = 3


def _get(ruta):
    r = requests.get(BASE + ruta, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _put(ruta, datos):
    r = requests.put(BASE + ruta, json=datos, timeout=TIMEOUT)
    if r.status_code in (400, 409):
        raise ValueError(r.json().get("error", "Solicitud inválida"))
    r.raise_for_status()
    return r.json()


# ------------------------------------------------------------------ sensores
def obtener_temperatura():
    return _get("/sensores/temperatura")


def obtener_humedad():
    return _get("/sensores/humedad")


def obtener_puerta():
    return _get("/sensores/puerta")


# ---------------------------------------------------------------- actuadores
def obtener_ventilador():
    return _get("/actuadores/ventilador")


def poner_ventilador(modo=None, velocidad=None, *, requiere_manual=False):
    cuerpo = {}
    if modo is not None:
        cuerpo["modo"] = modo
    if velocidad is not None:
        cuerpo["velocidad"] = velocidad
        if requiere_manual:
            cuerpo["requiere_manual"] = True
    return _put("/actuadores/ventilador", cuerpo)


def obtener_alarma():
    return _get("/actuadores/alarma")


def armar_alarma(armada=True):
    return _put("/actuadores/alarma", {"armada": armada})


def silenciar_alarma():
    return _put("/actuadores/alarma", {"silenciada": True})


# ------------------------------------------------------------ umbrales/estado
def obtener_umbrales():
    return _get("/umbrales")


def poner_umbrales(**umbrales):
    return _put("/umbrales", umbrales)


def obtener_estado():
    return _get("/estado")


# ------------------------------------------------- textos listos para Telegram
def texto_temperatura():
    d = obtener_temperatura()
    return f"🌡️ Temperatura: {d['valor']} {d['unidad']}"


def texto_humedad():
    d = obtener_humedad()
    return f"💧 Humedad: {d['valor']} {d['unidad']}"


def texto_puerta():
    d = obtener_puerta()
    return f"🚪 Puerta: {d['estado']}"


def texto_ventilador():
    return _formatear_ventilador(obtener_ventilador())


def _formatear_ventilador(d):
    estado = "encendido" if d["encendido"] else "apagado"
    return f"🌀 Ventilador: {estado}, {d['rpm']} RPM ({d['velocidad_pct']} %), modo {d['modo']}"


def cambiar_modo_ventilador(modo):
    d = poner_ventilador(modo=modo)
    return f"🌀 Modo del ventilador: {'manual' if d['modo'] == 'manual' else 'automático'}."


def texto_alarma():
    return _formatear_alarma(obtener_alarma())


def _formatear_alarma(d):
    if d["activa"]:
        return "🚨 Alarma ACTIVA: " + ", ".join(d["causas"])
    if d["silenciada"]:
        return "🔕 Alarma silenciada (sigue la causa: " + ", ".join(d["causas"]) + ")"
    return "✅ Alarma sin disparar (" + ("armada" if d["armada"] else "desarmada") + ")"


def texto_estado():
    estado = obtener_estado()
    sensores = estado["sensores"]
    actuadores = estado["actuadores"]
    temperatura = sensores["temperatura"]
    humedad = sensores["humedad"]
    simulacion = "en ejecución" if estado["corriendo"] else "pausada"
    return "\n".join([
        "📚 Estado de Biboteca",
        f"🧪 Simulación {simulacion}",
        f"🌡️ Temperatura: {temperatura['valor']:.1f} {temperatura['unidad']}",
        f"💧 Humedad: {humedad['valor']:.1f} {humedad['unidad']}",
        f"🚪 Puerta: {sensores['puerta']['estado']}",
        _formatear_ventilador(actuadores["ventilador"]),
        _formatear_alarma(actuadores["alarma"]),
    ])


def comando_ventilador(*args, requiere_manual=False):
    """/ventilador            -> estado
    /ventilador auto        -> modo automático
    /ventilador 60          -> manual al 60 %
    /ventilador manual 60   -> manual al 60 %"""
    if not args:
        return texto_ventilador()
    if requiere_manual:
        uso = "⚠️ Usa /ventilador seguido de un número entero entre 0 y 100."
        if len(args) != 1 or not args[0].isascii() or not args[0].isdecimal() or len(args[0]) > 3:
            return uso
        velocidad = int(args[0])
        if velocidad > 100:
            return uso
        try:
            d = poner_ventilador(velocidad=velocidad, requiere_manual=True)
        except ValueError as error:
            return f"⚠️ {error}"
        return f"🌀 Velocidad manual configurada: {d['velocidad_manual']} %."
    try:
        if args[0] == "auto":
            poner_ventilador(modo="auto")
        elif args[0] == "manual" and len(args) == 1:
            poner_ventilador(modo="manual")
        else:
            poner_ventilador(velocidad=int(args[-1]))
    except ValueError as e:
        return f"⚠️ {e}. Uso: /ventilador auto | /ventilador 0-100"
    return texto_ventilador()


def comando_alarma(*args):
    """/alarma  |  /alarma armar  |  /alarma desarmar  |  /alarma silenciar"""
    if args:
        accion = args[0].lower()
        if accion == "armar":
            armar_alarma(True)
        elif accion == "desarmar":
            armar_alarma(False)
        elif accion == "silenciar":
            silenciar_alarma()
        else:
            return "⚠️ Uso: /alarma armar | desarmar | silenciar"
    return texto_alarma()
