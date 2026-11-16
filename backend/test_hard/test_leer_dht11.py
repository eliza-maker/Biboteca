"""Prueba del ciclo de lectura del DHT11 (promedia hasta tres muestras).

Se ejecuta sin Raspberry Pi: simula las librerías board, digitalio y
adafruit_dht y comprueba la lógica de leer_dht11() con tres intentos.
"""
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "domotica"))

# Stubs de las librerías de hardware para poder importar hardware.py sin GPIO.
board_mod = types.ModuleType("board")
for pin in ("D3", "D4", "D17", "D23"):
    setattr(board_mod, pin, pin)
sys.modules["board"] = board_mod

digitalio_mod = types.ModuleType("digitalio")


class _DigitalInOut:
    def __init__(self, pin):
        self.pin = pin
        self.direction = None
        self.pull = None
        self.value = False

    def deinit(self):
        pass


class _Direction:
    INPUT = "in"
    OUTPUT = "out"


class _Pull:
    UP = "up"


digitalio_mod.DigitalInOut = _DigitalInOut
digitalio_mod.Direction = _Direction
digitalio_mod.Pull = _Pull
sys.modules["digitalio"] = digitalio_mod

dht_mod = types.ModuleType("adafruit_dht")


class _DHT11:
    def __init__(self, pin):
        self.pin = pin


dht_mod.DHT11 = _DHT11
sys.modules["adafruit_dht"] = dht_mod

import hardware  # noqa: E402


class FakeDHT:
    """Simula self._dht devolviendo lecturas predefinidas por intento.

    Cada elemento de `lecturas` puede ser:
      - (temperatura, humedad): lectura válida
      - None: lectura inválida (temperatura y humedad None)
      - "error": lanza RuntimeError al leer la temperatura
    """

    def __init__(self, lecturas):
        self._lecturas = list(lecturas)
        self._i = 0

    def _peek(self):
        return self._lecturas[self._i] if self._i < len(self._lecturas) else None

    @property
    def temperature(self):
        lectura = self._peek()
        if lectura == "error":
            self._i += 1
            raise RuntimeError("error de lectura simulado")
        return None if lectura is None else lectura[0]

    @property
    def humidity(self):
        lectura = self._peek()
        self._i += 1
        return None if lectura is None else lectura[1]

    def exit(self):
        pass


class DHT11CycleTest(unittest.TestCase):
    def _hardware(self, lecturas):
        lector = hardware.Hardware()
        lector._dht = FakeDHT(lecturas)
        return lector

    def test_promedia_tres_lecturas_validas(self):
        with mock.patch.object(hardware.time, "sleep"):
            lector = self._hardware([(20.0, 40.0), (22.0, 44.0), (21.0, 42.0)])
            self.assertEqual(lector.leer_dht11(), (21.0, 42.0))
            self.assertEqual(lector._dht._i, 3)  # consumió exactamente 3 intentos

    def test_descarta_lectura_invalida(self):
        with mock.patch.object(hardware.time, "sleep"):
            lector = self._hardware([(20.0, 40.0), None, (22.0, 44.0)])
            self.assertEqual(lector.leer_dht11(), (21.0, 42.0))

    def test_descarta_error_de_lectura(self):
        with mock.patch.object(hardware.time, "sleep"):
            lector = self._hardware(["error", (22.0, 44.0), (21.0, 42.0)])
            self.assertEqual(lector.leer_dht11(), (21.5, 43.0))

    def test_sin_lecturas_validas_devuelve_none(self):
        with mock.patch.object(hardware.time, "sleep"):
            lector = self._hardware([None, None, None])
            self.assertEqual(lector.leer_dht11(), (None, None))


if __name__ == "__main__":
    unittest.main()
