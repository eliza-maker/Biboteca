"""Lectura del DHT11 en una Raspberry Pi 3."""
from math import isfinite


class Hardware:
    def __init__(self):
        import adafruit_dht
        import board

        # DATA en BCM GPIO4 (pin físico 7 del conector de 40 pines).
        self._dht = adafruit_dht.DHT11(board.D4, use_pulseio=False)

    def leer_dht11(self):
        """Devuelve temperatura en °C y humedad relativa en %, de la misma muestra."""
        temperatura = self._dht.temperature
        humedad = self._dht.humidity
        if (temperatura is None or humedad is None
                or not isfinite(temperatura) or not 0 <= humedad <= 100):
            raise RuntimeError("Lectura inválida del DHT11")
        return temperatura, humedad
