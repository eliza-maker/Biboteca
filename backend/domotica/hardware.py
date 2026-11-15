"""Lectura del DHT11 en una Raspberry Pi 3."""
import time
import board
import adafruit_dht

class Hardware:
    def __init__(self):
        
        # DATA en BCM GPIO4 (pin físico 7 del conector de 40 pines).
        self._dht = adafruit_dht.DHT11(board.D4)

    def leer_dht11(self):
        count = 0            
        while count < 5:
                try:
                        temp = self._dht.temperature
                        hum = self._dht.humidity
                        print(f" tem: {temp}, hum: {hum}")
                        time.sleep(2.0)
                        continue
                except RuntimeError as error:
                        print(f"error de lectura: {error.args[0]}")
                        time.sleep(2.0)
                        continue
                except Exception as error:
                        self._dht.exit()
                        raise error
        
                time.sleep(2.0)
                count = count + 1
        return temp, hum
                
    def cerrar(self):
        """Libera los recursos de captura del sensor."""
        self._dht.exit()
