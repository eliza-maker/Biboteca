import time
import board
import adafruit_dht

sensor = adafruit_dht.DHT11(board.D4)

while True:
	try:
		temp = sensor.temperature
		hum = sensor.humidity
		print(f" tem: {temp}, hum: {hum}")
		time.sleep(2.0)
		continue
	except RuntimeError as error:
		print(f"error de lectura: {error.args[0]}")
		time.sleep(2.0)
		continue
	except Exception as error:
		sensor.exit()
		raise error
	
	time.sleep(2.0)
