"""Lectura del DHT11 y control de actuadores en una Raspberry Pi 3.

Pines (numeración BCM / GPIO):
  - GPIO4 : DHT11 (temperatura y humedad, entrada)
  - GPIO3 : sensor magnético de puerta (entrada con pull-up)
  - GPIO17: buzzer (salida)
  - GPIO23: LED que simula el motor del ventilador (salida)
"""
import time

import board
import digitalio
import adafruit_dht


class Hardware:
    def __init__(self):
        # DATA en BCM GPIO4 (pin físico 7 del conector de 40 pines).
        self._dht = adafruit_dht.DHT11(board.D4)

        self._puerta = digitalio.DigitalInOut(board.D3)
        self._puerta.direction = digitalio.Direction.INPUT
        self._puerta.pull = digitalio.Pull.UP

        self._buzzer = digitalio.DigitalInOut(board.D17)
        self._buzzer.direction = digitalio.Direction.OUTPUT
        self._buzzer.value = False

        self._motor = digitalio.DigitalInOut(board.D23)
        self._motor.direction = digitalio.Direction.OUTPUT
        self._motor.value = False

    def leer_dht11(self):
        """Promedia las muestras válidas de tres intentos de lectura."""
        muestras = []

        for intento in range(3):
            try:
                temperatura = self._dht.temperature
                humedad = self._dht.humidity
                if temperatura is not None and humedad is not None:
                    muestras.append((temperatura, humedad))
            except RuntimeError as error:
                print(f"Error de lectura: {error}")
            except Exception:
                self._dht.exit()
                raise

            if intento < 2:
                time.sleep(2.0)

        if not muestras:
            return None, None

        temperaturas, humedades = zip(*muestras)
        return sum(temperaturas) / len(muestras), sum(humedades) / len(muestras)

    def leer_puerta(self):
        """True si la puerta está abierta (contacto magnético separado).

        Con pull-up, el imán alineado cierra el contacto a GND y se lee False.
        """
        return bool(self._puerta.value)

    def aplicar_actuadores(self, ventilador_encendido, alarma_activa):
        """Enciende o apaga el LED del motor y el buzzer según el estado."""
        self._motor.value = bool(ventilador_encendido)
        self._buzzer.value = bool(alarma_activa)

    def cerrar(self):
        """Libera los recursos de captura y los pines de salida."""
        self._dht.exit()
        self._puerta.deinit()
        self._buzzer.deinit()
        self._motor.deinit()
