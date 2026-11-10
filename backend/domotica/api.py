"""API REST de domótica (simulada). Ejecutar con: python api.py

El servidor es la única fuente de verdad: simula los sensores, aplica la lógica de los
actuadores y expone una URL por variable y por actuador. El panel HTML y el bot de
Telegram consultan/modifican lo mismo a través de estas URLs.
"""
from pathlib import Path #Se importa Path para poder llamar a frontend/
import random
import threading
import time

from flask import Flask, abort, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")
lock = threading.Lock()
MAX_RPM = 3000

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
    """Hilo que avanza el sistema cada 0.2 s: sensores -> motor -> alarma."""
    while True:
        time.sleep(0.2)
        with lock:
            if not ST["corriendo"]:
                continue
            s, v, u, a = ST["sim"], ST["ventilador"], ST["umbrales"], ST["alarma"]
            enfria = v["rpm"] / MAX_RPM * 8  # el ventilador enfría el ambiente
            ST["temperatura"] += (s["temperatura_ambiente"] - enfria - ST["temperatura"]) * 0.06 \
                + random.uniform(-0.15, 0.15)
            ST["humedad"] += (s["humedad_ambiente"] - ST["humedad"]) * 0.08 + random.uniform(-0.4, 0.4)
            ST["humedad"] = min(100.0, max(0.0, ST["humedad"]))

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


# --------------------------------------------------------------------- vistas
def v_temperatura():
    return {"valor": round(ST["temperatura"], 1), "unidad": "°C"}


def v_humedad():
    return {"valor": round(ST["humedad"], 1), "unidad": "%HR"}


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
    return {
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
@app.get("/")
def panel():
    return send_from_directory(Path(__file__).resolve().parent.parent / "frontend", "panel-sensores.html") #ruta correcta panel de sensores


@app.get("/api")
def indice():
    return jsonify(
        lectura=["/api/estado", "/api/sensores/temperatura", "/api/sensores/humedad",
                 "/api/sensores/puerta", "/api/actuadores/ventilador", "/api/actuadores/alarma",
                 "/api/umbrales"],
        escritura=["PUT /api/actuadores/ventilador", "PUT /api/actuadores/alarma", "PUT /api/umbrales",
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
    """Cuerpo: {"modo": "auto"|"manual", "velocidad": 0-100}. Si solo llega velocidad, pasa a manual."""
    d = _json()
    with lock:
        v = ST["ventilador"]
        if "velocidad" in d:
            v["velocidad_manual"] = int(_num(d, "velocidad", 0, 100))
            v["modo"] = "manual"
        if "modo" in d:
            if d["modo"] not in ("auto", "manual"):
                abort(400, "'modo' debe ser 'auto' o 'manual'")
            v["modo"] = d["modo"]
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
        ST["sim"]["temperatura_ambiente"] = _num(d, "ambiente", 0, 60)
        return jsonify(ST["sim"])


@app.put("/api/simulacion/humedad")
def sim_humedad():
    d = _json()
    with lock:
        ST["sim"]["humedad_ambiente"] = _num(d, "ambiente", 0, 100)
        return jsonify(ST["sim"])


@app.put("/api/simulacion/puerta")
def sim_puerta():
    d = _json()
    with lock:
        ST["puerta_abierta"] = _bool(d, "abierta")
        return jsonify(v_puerta())


@app.put("/api/simulacion/ejecucion")
def sim_ejecucion():
    d = _json()
    with lock:
        ST["corriendo"] = _bool(d, "activa")
        return jsonify(corriendo=ST["corriendo"])


if __name__ == "__main__":
    threading.Thread(target=_simular, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, threaded=True)
