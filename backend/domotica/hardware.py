"""Lectura del DHT11 en una Raspberry Pi 3."""
import time
import board
import adafruit_dht

class Hardware:
    def __init__(self):
        
        # DATA en BCM GPIO4 (pin físico 7 del conector de 40 pines).
        self._dht = adafruit_dht.DHT11(board.D4)

    def leer_dht11(self):
        """Promedia las muestras válidas de cinco intentos de lectura."""
        muestras = []

        for intento in range(5):
            try:
                temperatura = self._dht.temperature
                humedad = self._dht.humidity
                if temperatura is not None and humedad is not None:
                    muestras.append((temperatura, humedad))
            except RuntimeError as error:
                print(f"Error de lectura: {error}", flush=True)

            if intento < 4:
                time.sleep(2.0)

        if not muestras:
            return None, None

        temperaturas, humedades = zip(*muestras)
        return sum(temperaturas) / len(muestras), sum(humedades) / len(muestras)
                
    def cerrar(self):
        """Libera los recursos de captura del sensor."""
        try:
            self._dht.exit()
        finally:
            switch = getattr(self, "_switch", None)
            if switch is not None:
                switch.close()

    def _init_(self, al_abrir_puerta=None):
        self._switch = Button(3, pull_up=True, bounce_time=0.1)
        
        # Asignamos el evento a una función externa
        if al_abrir_puerta:
            self._switch.when_released = al_abrir_puerta
