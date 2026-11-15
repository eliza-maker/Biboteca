"""Sensores y buzzer de la Raspberry Pi 3."""
from contextlib import ExitStack
from math import isfinite

import board
import adafruit_dht
from digitalio import DigitalInOut


class Hardware:
    def __init__(self):
        with ExitStack() as recursos:
            # DATA del DHT11 en BCM GPIO4 (pin físico 7).
            self._dht = adafruit_dht.DHT11(board.D4)
            recursos.callback(self._dht.exit)

            # El contacto une GPIO3 con GND. GPIO3 tiene un pull-up en la placa.
            self._contacto = DigitalInOut(board.D3)
            recursos.callback(self._contacto.deinit)
            self._contacto.switch_to_input()

            self._buzzer = DigitalInOut(board.D17)
            recursos.callback(self._buzzer.deinit)
            self._buzzer.switch_to_output(value=False)
            recursos.callback(setattr, self._buzzer, "value", False)
            self._recursos = recursos.pop_all()

    def leer_dht11(self):
        """Devuelve una muestra de temperatura y humedad."""
        temperatura = self._dht.temperature
        humedad = self._dht.humidity
        if (temperatura is None or humedad is None
                or not isfinite(temperatura) or not 0 <= humedad <= 100):
            raise RuntimeError("Lectura inválida del DHT11")
        return temperatura, humedad

    def actualizar_buzzer_por_contacto(self):
        """Activa el buzzer mientras el imán mantenga cerrado el contacto."""
        self._buzzer.value = not self._contacto.value

    def cerrar(self):
        """Apaga el buzzer y libera los pines y el DHT11."""
        self._recursos.close()
