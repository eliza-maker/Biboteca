from datetime import datetime
import csv
import os


def guardar_registro(temperatura, luz, ventilador, lampara):

    archivo = "datos.csv"

    existe = os.path.isfile(archivo)

    with open(archivo, "a", newline="") as f:

        writer = csv.writer(f)

        if not existe:
            writer.writerow([
                "fecha",
                "temperatura",
                "luz",
                "ventilador",
                "lampara"
            ])

        writer.writerow([
            datetime.now(),
            temperatura,
            luz,
            ventilador,
            lampara
        ])