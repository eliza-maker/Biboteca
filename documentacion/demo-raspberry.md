# Demo de Biboteca en Raspberry Pi

La Raspberry ejecuta la API y el bot de Telegram. El modo predeterminado usa el panel y el simulador. Para probar el sensor físico, sigue la sección 5.

## 1. Preparar la Raspberry

En la Pi, ejecuta `sudo raspi-config` y habilita **SSH** en **Interface Options**. Ejecuta `whoami` para ver tu usuario y `hostname -I` para encontrar su IP en la red local. Conecta el PC a esa misma red. [Acceso remoto en Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/remote-access.html)

## 2. Pasar los archivos desde Windows

Abre PowerShell en la raíz de Biboteca. Cambia `usuario` y `192.168.1.50` por los valores de tu Raspberry. El paquete incluye los archivos que tienes ahora en tu carpeta de trabajo y excluye las credenciales, el entorno virtual de Windows y las cachés de Python.

```powershell
$destino = 'usuario@192.168.1.50'
$paquete = Join-Path $env:TEMP 'biboteca-demo.tar.gz'
tar.exe -czf $paquete --exclude '.env' --exclude '__pycache__' --exclude '*.pyc' .gitignore backend control frontend documentacion configuracion.py main.py requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el paquete de Biboteca.' }
scp $paquete "${destino}:biboteca-demo.tar.gz"
ssh $destino
```

Ya dentro de la Raspberry, descomprime el paquete en una carpeta nueva:

```bash
mkdir -p ~/Biboteca
tar -xzf ~/biboteca-demo.tar.gz -C ~/Biboteca
cd ~/Biboteca
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Si `venv` indica que falta `ensurepip`, instala `python3-venv` con `sudo apt install python3-venv` y repite la creación del entorno. [Python en Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/os.html#use-python-on-a-raspberry-pi)

## 3. Configurar Telegram e iniciar los procesos

En la Raspberry, desde `~/Biboteca`, crea `.env` si todavía no existe. En el editor, rellena `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` con los valores del bot y del chat que ya usas. Guarda con `Ctrl+O`, `Enter` y sal con `Ctrl+X`.

```bash
if [ ! -f backend/bot/.env ]; then
  cp backend/bot/.env.example backend/bot/.env
fi
chmod 600 backend/bot/.env
nano backend/bot/.env
```

En esa sesión SSH, arranca la API y déjala abierta:

```bash
.venv/bin/python backend/domotica/api.py
```

Detén el bot de Windows con `Ctrl+C` si está usando el mismo token. Abre otra ventana de PowerShell, conéctate otra vez con `ssh usuario@192.168.1.50` y, dentro de la Pi, arranca el bot:

```bash
cd ~/Biboteca
.venv/bin/python -m backend.bot.telegram_bot
```

## 4. Abrir el panel y probar la demo

En el navegador de la Raspberry, abre `http://127.0.0.1:5000/`. Si vas a usar el navegador de Windows, abre una tercera ventana de PowerShell y deja este túnel abierto mientras haces la prueba. La API sigue escuchando solo en la Raspberry y el túnel conecta el puerto `8080` del PC con ella. [Reenvío local de puertos con SSH](https://man.openbsd.org/ssh#L)

```powershell
ssh -o ExitOnForwardFailure=yes -N -L 127.0.0.1:8080:127.0.0.1:5000 usuario@192.168.1.50
```

En Windows, abre [el panel por el túnel](http://127.0.0.1:8080/) y haz estas comprobaciones:

1. Desde el chat autorizado, envía `/start`. Aparece el teclado de Biboteca. Toca **Estado** y comprueba que aparecen temperatura, humedad y puerta. Las lecturas pueden variar entre la consulta del bot y la del panel mientras corre la simulación.
2. Con la simulación en marcha, toca **Ventilador → Manual → 60 %**. El bot debe confirmar el ajuste y el panel debe mostrar **Manual** y **60 %**. Las RPM simuladas suben gradualmente.
3. Toca **Automático** en el bot. El panel debe volver a **Auto**. Abre la puerta simulada desde el panel y pide `/estado` para comprobar que Telegram también la muestra abierta.

Si el panel no abre desde Windows, comprueba que la API y el túnel sigan activos. Si el bot informa un conflicto de Telegram, comprueba que no haya otra instancia con el mismo token. Si informa que no pudo consultar el estado, revisa que la API esté ejecutándose en la Raspberry. Para terminar la demo, pulsa `Ctrl+C` en cada sesión.

## 5. Cambiar al DHT11 físico en la Raspberry Pi 3

Apaga la Raspberry antes de conectar el DHT11. Usa los números físicos del conector de 40 pines de la Raspberry.

| DHT11 | Raspberry Pi 3 |
| --- | --- |
| VCC | 3,3 V, pin físico 1 |
| DATA | BCM GPIO4, pin físico 7 |
| GND | Tierra, pin físico 6 |

Si el sensor viene sin resistencia pull-up, conecta una de 4,7 a 10 kΩ entre DATA y 3,3 V. Para un módulo de tres pines, sigue las etiquetas impresas en el módulo. En el sensor de cuatro patas, deja NC sin conectar. [Cableado del DHT11](https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging)

En la Raspberry, desde la carpeta del proyecto y con el entorno virtual de la sección 2 creado, instala las dependencias del GPIO y del DHT11. [Instalación de Blinka en Raspberry Pi](https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi)

```bash
sudo apt install libgpiod-dev python3-libgpiod
.venv/bin/python -m pip install adafruit-blinka adafruit-circuitpython-dht
```

En `backend/domotica/api.py`, cambia `html: bool = True` por `html: bool = False` y reinicia la API con el comando de la sección 3. Arranca el bot actualizado y envía `/estado`, `/temperatura` o `/humedad`. El DHT11 se consulta cada dos segundos. Si falla una lectura, el bot mostrará «sin lectura del DHT11» hasta recibir una muestra válida. El modo físico ofrece temperatura y humedad. El panel, la puerta, el ventilador y la alarma están disponibles en modo simulación.
