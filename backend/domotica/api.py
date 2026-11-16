"""API REST de domótica para el panel simulado o el DHT11 de la Raspberry Pi."""
from pathlib import Path
import random
import threading
import time

from flask import Flask, abort, jsonify, request, send_from_directory

html: bool = False  # True: simulación HTML. False: DHT11 en la Raspberry Pi.

app = Flask(__name__, static_folder="static")
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
lock = threading.Lock()
MAX_RPM = 3000
MUESTRAS_POR_PROMEDIO = 4
hardware = None
muestras_dht = []
promedio_dht = (None, None)
_trabajador = None
_detener = None

ST = {
    "corriendo": True,
    "temperatura": 24.0,
    "humedad": 50.0,
    "puerta_abierta": False,
    # Entradas de la simulación (el "mundo físico"). Con sensores reales se reemplazan.
    "sim": {"temperatura_ambiente": 24.0, "humedad_ambiente": 50.0},
    "ventilador": {"modo": "auto", "velocidad_manual": 0, "rpm": 0.0},
    "alarma": {"armada": True, "silenciada": False, "activa": False, "causas": []},
    "umbrales": {"ventilador_on": 28.0, "alarma_temperatura": 38.0, "alarma_humedad": 85.0},
}
LIMITES = {"ventilador_on": (15, 45), "alarma_temperatura": (20, 60), "alarma_humedad": (30, 100)}


# ---------------------------------------------------------------- simulación
def _simular():
    """Avanza un paso de la simulación con el estado bloqueado."""
    if not ST["corriendo"]:
        return
    s, v = ST["sim"], ST["ventilador"]
    enfria = v["rpm"] / MAX_RPM * 8  # el ventilador enfría el ambiente
    ST["temperatura"] += (s["temperatura_ambiente"] - enfria - ST["temperatura"]) * 0.06 \
        + random.uniform(-0.15, 0.15)
    ST["humedad"] += (s["humedad_ambiente"] - ST["humedad"]) * 0.08 + random.uniform(-0.4, 0.4)
    ST["humedad"] = min(100.0, max(0.0, ST["humedad"]))
    _controlar_actuadores()


def _controlar_actuadores():
    """Decide ventilador y alarma a partir del estado; el cálculo es el mismo en ambos modos."""
    v, u, a = ST["ventilador"], ST["umbrales"], ST["alarma"]

    # Actuador 1: ventilador (la temperatura decide su velocidad en modo auto)
    if v["modo"] == "auto":
        objetivo = min(1.0, max(0.0, (ST["temperatura"] - u["ventilador_on"]) / 8))
    else:
        objetivo = v["velocidad_manual"] / 100
    v["rpm"] += (objetivo * MAX_RPM - v["rpm"]) * 0.12
    if objetivo == 0 and v["rpm"] < 5:
        v["rpm"] = 0.0

    # Actuador 2: alarma (temperatura, humedad o puerta abierta con alarma armada)
    causas = []
    if ST["temperatura"] >= u["alarma_temperatura"]:
        causas.append("temperatura alta")
    if ST["humedad"] >= u["alarma_humedad"]:
        causas.append("humedad alta")
    if a["armada"] and ST["puerta_abierta"]:
        causas.append("puerta abierta")
    a["causas"] = causas
    if not causas:
        a["silenciada"] = False
    a["activa"] = bool(causas) and not a["silenciada"]


def _inicializar_hardware():
    """Crea el lector DHT11 si no existe. Devuelve el mensaje de error o None."""
    global hardware
    if hardware is not None:
        return None
    try:
        # Las librerías GPIO/DHT11 solo se importan al usar hardware real, para que
        # la simulación funcione también en equipos que no las tengan instaladas.
        if __package__:
            from .hardware import Hardware
        else:
            from hardware import Hardware
        hardware = Hardware()
        return None
    except Exception as error:
        return f"No se pudo inicializar el hardware: {error}"


def _cerrar_hardware():
    """Libera el lector DHT11."""
    global hardware
    if hardware is not None:
        try:
            hardware.cerrar()
        except Exception as error:
            app.logger.warning("No se pudo cerrar el hardware: %s", error)
        finally:
            hardware = None


def _ciclo_simulacion(detener):
    """Avanza la simulación cada 250 ms mientras esté en ejecución."""
    while not detener.wait(0.25):
        with lock:
            _simular()


def _ciclo_hardware(detener):
    """Lee los sensores reales, decide actuadores y actualiza las variables globales."""
    global promedio_dht
    while not detener.is_set():
        with lock:
            sensor = hardware
        if sensor is None:
            break
        error_lectura = False
        try:
            temperatura, humedad = sensor.leer_dht11()
        except Exception as error:
            app.logger.warning("Error de lectura del DHT11: %s", error)
            temperatura = humedad = None
            error_lectura = True
        with lock:
            if detener.is_set() or hardware is not sensor:
                break
            try:
                if temperatura is not None and humedad is not None:
                    muestras_dht.append((temperatura, humedad))
                    while len(muestras_dht) > MUESTRAS_POR_PROMEDIO:
                        muestras_dht.pop(0)
                else:
                    muestras_dht.clear()
                if muestras_dht:
                    temperaturas, humedades = zip(*muestras_dht)
                    promedio_dht = (sum(temperaturas) / len(temperaturas),
                                    sum(humedades) / len(humedades))
                    ST["temperatura"] = promedio_dht[0]
                    ST["humedad"] = promedio_dht[1]
                else:
                    promedio_dht = (None, None)
                ST["puerta_abierta"] = sensor.leer_puerta()
                _controlar_actuadores()
                sensor.aplicar_actuadores(
                    ventilador_encendido=ST["ventilador"]["rpm"] > 30,
                    alarma_activa=ST["alarma"]["activa"],
                )
            except Exception as error:
                app.logger.warning("Error leyendo puerta o aplicando actuadores: %s", error)
        detener.wait(2.0 if error_lectura else 0.1)


def _detener_trabajador():
    """Detiene el ciclo activo (simulación o hardware)."""
    global _trabajador, _detener
    if _detener is not None:
        _detener.set()
    if _trabajador is not None and _trabajador.is_alive():
        _trabajador.join(timeout=2)
    _trabajador = None
    _detener = None


def _iniciar_trabajador():
    """Arranca el ciclo correspondiente al modo actual."""
    global _trabajador, _detener
    _detener_trabajador()
    _detener = threading.Event()
    objetivo = _ciclo_simulacion if html else _ciclo_hardware
    _trabajador = threading.Thread(target=objetivo, args=(_detener,), daemon=True)
    _trabajador.start()


# --------------------------------------------------------------------- vistas
def v_temperatura():
    valor = ST["temperatura"] if html else promedio_dht[0]
    return {"valor": None if valor is None else round(valor, 1), "unidad": "°C"}


def v_humedad():
    valor = ST["humedad"] if html else promedio_dht[1]
    return {"valor": None if valor is None else round(valor, 1), "unidad": "%HR"}


def v_puerta():
    ab = ST["puerta_abierta"]
    return {"abierta": ab, "estado": "abierta" if ab else "cerrada"}


def v_ventilador():
    v = ST["ventilador"]
    return {"modo": v["modo"], "velocidad_manual": v["velocidad_manual"], "rpm": round(v["rpm"]),
            "velocidad_pct": round(v["rpm"] / MAX_RPM * 100), "encendido": v["rpm"] > 30}


def v_alarma():
    a = ST["alarma"]
    return {"armada": a["armada"], "silenciada": a["silenciada"], "activa": a["activa"],
            "causas": list(a["causas"])}


def estado():
    if not html:
        return {
            "modo": "hardware",
            "sensores": {"temperatura": v_temperatura(), "humedad": v_humedad()},
        }
    return {
        "modo": "simulacion",
        "corriendo": ST["corriendo"],
        "sensores": {"temperatura": v_temperatura(), "humedad": v_humedad(), "puerta": v_puerta()},
        "simulacion": dict(ST["sim"]),
        "actuadores": {"ventilador": v_ventilador(), "alarma": v_alarma()},
        "umbrales": dict(ST["umbrales"]),
    }


# ----------------------------------------------------------------- utilidades
def _json():
    return request.get_json(silent=True) or {}


def _num(d, clave, lo, hi):
    try:
        x = float(d[clave])
    except (KeyError, TypeError, ValueError):
        abort(400, f"Falta '{clave}' o no es un número")
    if not lo <= x <= hi:
        abort(400, f"'{clave}' debe estar entre {lo} y {hi}")
    return x


def _bool(d, clave):
    if not isinstance(d.get(clave), bool):
        abort(400, f"'{clave}' debe ser true o false")
    return d[clave]


@app.errorhandler(400)
def _error400(e):
    return jsonify(error=e.description), 400


@app.after_request
def _cors(r):  # permite abrir el HTML desde otro origen (p. ej. Live Server)
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    r.headers["Access-Control-Allow-Methods"] = "GET, PUT, OPTIONS"
    return r


# ------------------------------------------------------------------ endpoints
@app.errorhandler(404)
def _error404(error):
    return jsonify(error=error.description), 404


def _requiere_simulacion():
    if not html:
        abort(404, "Ruta disponible solo en modo simulación.")


@app.put("/api/modo")
def put_modo():
    global html, promedio_dht
    activar_html = _bool(_json(), "html")
    cambio = False
    with lock:
        if not activar_html:
            error = _inicializar_hardware()
            if error:
                app.logger.warning("%s", error)
                return jsonify(error=error), 503
        cambio = html != activar_html
        if cambio:
            html = activar_html
            if activar_html:
                _cerrar_hardware()
            muestras_dht.clear()
            promedio_dht = (None, None)
    # Reinicia el ciclo fuera del lock: el trabajador anterior también usa el lock.
    trabajador_activo = _trabajador is not None and _trabajador.is_alive()
    if cambio or (not html and not trabajador_activo):
        _iniciar_trabajador()
    with lock:
        return jsonify(estado())


@app.get("/")
def panel():
    return send_from_directory(FRONTEND_DIR, "panel-sensores.html")


@app.get("/api")
def indice():
    return jsonify(
        lectura=["/api/estado", "/api/sensores/temperatura", "/api/sensores/humedad",
                 "/api/sensores/puerta", "/api/actuadores/ventilador", "/api/actuadores/alarma",
                 "/api/umbrales"],
        escritura=["PUT /api/modo", "PUT /api/actuadores/ventilador", "PUT /api/actuadores/alarma", "PUT /api/umbrales",
                   "PUT /api/simulacion/temperatura", "PUT /api/simulacion/humedad",
                   "PUT /api/simulacion/puerta", "PUT /api/simulacion/ejecucion"])


@app.get("/api/estado")
def get_estado():
    with lock:
        return jsonify(estado())


# Sensores (solo lectura)
@app.get("/api/sensores/temperatura")
def get_temperatura():
    with lock:
        return jsonify(v_temperatura())


@app.get("/api/sensores/humedad")
def get_humedad():
    with lock:
        return jsonify(v_humedad())


@app.get("/api/sensores/puerta")
def get_puerta():
    with lock:
        return jsonify(v_puerta())


# Actuadores
@app.get("/api/actuadores/ventilador")
def get_ventilador():
    with lock:
        return jsonify(v_ventilador())


@app.put("/api/actuadores/ventilador")
def put_ventilador():
    """Actualiza modo o velocidad. requiere_manual exige que el modo actual sea manual."""
    d = _json()
    with lock:
        v = ST["ventilador"]
        modo = d.get("modo", v["modo"])
        if modo not in ("auto", "manual"):
            abort(400, "'modo' debe ser 'auto' o 'manual'")
        if "velocidad" in d:
            if "requiere_manual" in d and _bool(d, "requiere_manual") and v["modo"] != "manual":
                return jsonify(error="Activa el modo manual con /manual antes de cambiar la velocidad."), 409
            v["velocidad_manual"] = int(_num(d, "velocidad", 0, 100))
            modo = d.get("modo", "manual")
        v["modo"] = modo
        return jsonify(v_ventilador())


@app.get("/api/actuadores/alarma")
def get_alarma():
    with lock:
        return jsonify(v_alarma())


@app.put("/api/actuadores/alarma")
def put_alarma():
    """Cuerpo: {"armada": bool, "silenciada": bool}. Silenciar solo tiene efecto si hay una causa activa."""
    d = _json()
    with lock:
        a = ST["alarma"]
        if "armada" in d:
            a["armada"] = _bool(d, "armada")
        if "silenciada" in d:
            if _bool(d, "silenciada"):
                if a["causas"]:
                    a["silenciada"] = True
                    a["activa"] = False
            else:
                a["silenciada"] = False
        return jsonify(v_alarma())


# Umbrales
@app.get("/api/umbrales")
def get_umbrales():
    with lock:
        return jsonify(dict(ST["umbrales"]))


@app.put("/api/umbrales")
def put_umbrales():
    d = _json()
    with lock:
        for clave, (lo, hi) in LIMITES.items():
            if clave in d:
                ST["umbrales"][clave] = _num(d, clave, lo, hi)
        return jsonify(dict(ST["umbrales"]))


# Entradas de la simulación (con hardware real estas rutas desaparecen)
@app.put("/api/simulacion/temperatura")
def sim_temperatura():
    d = _json()
    with lock:
        _requiere_simulacion()
        ST["sim"]["temperatura_ambiente"] = _num(d, "ambiente", 0, 60)
        return jsonify(ST["sim"])


@app.put("/api/simulacion/humedad")
def sim_humedad():
    d = _json()
    with lock:
        _requiere_simulacion()
        ST["sim"]["humedad_ambiente"] = _num(d, "ambiente", 0, 100)
        return jsonify(ST["sim"])


@app.put("/api/simulacion/puerta")
def sim_puerta():
    d = _json()
    with lock:
        _requiere_simulacion()
        ST["puerta_abierta"] = _bool(d, "abierta")
        return jsonify(v_puerta())


@app.put("/api/simulacion/ejecucion")
def sim_ejecucion():
    d = _json()
    with lock:
        _requiere_simulacion()
        ST["corriendo"] = _bool(d, "activa")
        return jsonify(corriendo=ST["corriendo"])


if __name__ == "__main__":
    if not html:
        error = _inicializar_hardware()
        if error:
            print(f"Aviso: {error}. Activa la simulación desde el panel con «Volver a simulación».")
    _iniciar_trabajador()
    try:
        app.run(host="127.0.0.1", port=5000, threaded=True)
    finally:
        _detener_trabajador()
        with lock:
            _cerrar_hardware()
