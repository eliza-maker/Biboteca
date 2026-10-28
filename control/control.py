TEMP_ENCENDER = 30
TEMP_APAGAR = 27

LUZ_ENCENDER = 300
LUZ_APAGAR = 500

def control_automatico(temperatura, luz):
    
    ventilador = False
    lampara = False

    # Regla ventilador
    if temperatura > TEMP_ENCENDER:
        ventilador = True

    # Regla lámpara
    if luz < LUZ_ENCENDER:
        lampara = True

    return ventilador, lampara

def control_manual(estado_ventilador, estado_lampara):

    ventilador = estado_ventilador
    lampara = estado_lampara

    return ventilador, lampara