import paramiko
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
from PyQt5 import QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import sys
import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import logging

# Configurar el logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Datos de conexión SSH
raspi_ip = '192.168.0.49'
raspi_user = 'raspi'
raspi_password = 'raspi'  # Reemplaza esto con la contraseña correcta
json_remote_path = '/home/raspi/Desktop/PROYECTOFINAL/gas_monitor_data.json'

# Token del bot de Telegram
TELEGRAM_BOT_TOKEN = '7649547121:AAHqIksExg6Oxr_CjhYLA8qU4D9j2-kTuX4'

class GasMonitorApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Gases")
        self.setGeometry(100, 100, 1000, 800)

        # Widget principal
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout principal
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        # Widget de advertencias
        self.advertencia_label = QtWidgets.QLabel()
        self.advertencia_label.setStyleSheet("color: red;")
        self.layout.addWidget(self.advertencia_label)

        # Área de gráficos
        self.figure, self.axs = plt.subplots(5, 1, figsize=(10, 10), sharex=True)
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        # Actualizar los datos inicialmente al iniciar la aplicación
        self.actualizar_datos()

        # Temporizador para actualizar los datos automáticamente cada 5 segundos
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.actualizar_datos)
        self.timer.start(5000)  # 5 segundos

    def actualizar_datos(self):
        try:
            # Crear un cliente SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(raspi_ip, username=raspi_user, password=raspi_password)

            # Crear el cliente SFTP
            sftp = ssh.open_sftp()

            # Descargar el archivo JSON
            local_json_path = 'gas_monitor_data_local.json'  # Ruta donde se guardará localmente
            sftp.get(json_remote_path, local_json_path)

            # Cerrar la conexión SFTP y SSH
            sftp.close()
            ssh.close()

            # Leer el archivo JSON descargado y guardar los datos en una lista
            data_list = []
            with open(local_json_path, 'r') as file:
                for line in file:
                    try:
                        data = json.loads(line)
                        data_list.append(data)
                    except json.JSONDecodeError as e:
                        print(f"Error al leer una línea del archivo JSON: {e}")

            # Guardar los datos leídos en un archivo JSON local
            with open('gas_monitor_data_processed.json', 'w') as outfile:
                json.dump(data_list, outfile, indent=4)

            # Verificar condiciones para advertencias y mostrar en la interfaz
            advertencias = []
            for entry in data_list[-5:]:  # Solo las últimas 5 lecturas
                if entry['dht11']['humedad'] > 80:
                    advertencias.append("Humedad > 80%.")
                if entry['gases']['monoxido_carbono'] > 5000:
                    advertencias.append("CO alto.")
                if entry['gases']['gas_natural'] > 3000:
                    advertencias.append("Gas natural alto.")
                if entry['gases']['calidad_aire'] > 3500:
                    advertencias.append("Calidad de aire deficiente.")

            # Mostrar solo la última advertencia
            self.advertencia_label.setText(advertencias[-1] if advertencias else "Sin advertencias.")

            # Actualizar gráficos
            self.graficar_datos(data_list)

        except Exception as e:
            self.advertencia_label.setText(f"Error al conectarse a la Raspberry Pi o leer el archivo: {e}")

    def graficar_datos(self, data_list):
        # Limpiar los ejes antes de volver a dibujar
        for ax in self.axs:
            ax.clear()

        if not data_list:
            self.advertencia_label.setText("No hay datos disponibles para graficar.")
            self.canvas.draw()
            return

        # Preparar datos para graficar
        timestamps = [datetime.datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S") for entry in data_list]
        temperaturas = [entry['dht11']['temperatura'] for entry in data_list]
        humedades = [entry['dht11']['humedad'] for entry in data_list]
        monoxido_carbono = [entry['gases']['monoxido_carbono'] for entry in data_list]
        gas_natural = [entry['gases']['gas_natural'] for entry in data_list]
        calidad_aire = [entry['gases']['calidad_aire'] for entry in data_list]

        # Crear subplots
        self.axs[0].plot(timestamps, temperaturas, label='Temp (°C)', color='r')
        self.axs[0].set_ylabel('Temp (°C)')
        self.axs[0].legend()
        self.axs[0].grid(True)

        self.axs[1].plot(timestamps, humedades, label='Humedad (%)', color='b')
        self.axs[1].set_ylabel('Humedad (%)')
        self.axs[1].legend()
        self.axs[1].grid(True)

        self.axs[2].plot(timestamps, monoxido_carbono, label='CO', color='g')
        self.axs[2].set_ylabel('CO')
        self.axs[2].legend()
        self.axs[2].grid(True)

        self.axs[3].plot(timestamps, gas_natural, label='Gas Natural', color='y')
        self.axs[3].set_ylabel('Gas Natural')
        self.axs[3].legend()
        self.axs[3].grid(True)

        self.axs[4].plot(timestamps, calidad_aire, label='Calidad Aire', color='m')
        self.axs[4].set_ylabel('Calidad Aire')
        self.axs[4].legend()
        self.axs[4].grid(True)

        self.figure.tight_layout()
        self.canvas.draw()

# Función para solicitar y enviar los datos del sensor al recibir el comando /datos
async def enviar_datos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Leer los datos del archivo JSON procesado
        with open('gas_monitor_data_processed.json', 'r') as file:
            data_list = json.load(file)

        # Obtener la última lectura
        ultimo_dato = data_list[-1] if data_list else None
        if ultimo_dato:
            timestamp = ultimo_dato['timestamp']
            temperatura = ultimo_dato['dht11']['temperatura']
            humedad = ultimo_dato['dht11']['humedad']
            co = ultimo_dato['gases']['monoxido_carbono']
            gas_natural = ultimo_dato['gases']['gas_natural']
            calidad_aire = ultimo_dato['gases']['calidad_aire']

            # Formatear los datos como mensaje de respuesta
            mensaje = (
                f"Última lectura de sensores:\n"
                f"Timestamp: {timestamp}\n"
                f"Temperatura: {temperatura} °C\n"
                f"Humedad: {humedad} %\n"
                f"Monóxido de Carbono: {co}\n"
                f"Gas Natural: {gas_natural}\n"
                f"Calidad del Aire: {calidad_aire}"
            )
        else:
            mensaje = "No se encontraron datos disponibles."

        # Enviar los datos a través del bot
        await update.message.reply_text(mensaje)

    except Exception as e:
        await update.message.reply_text(f"Error al obtener los datos: {e}")

# Función para generar el gráfico y enviarlo a Telegram
async def enviar_grafico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Leer los datos del archivo JSON procesado
        with open('gas_monitor_data_processed.json', 'r') as file:
            data_list = json.load(file)

        # Preparar datos para graficar
        timestamps = [datetime.datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S") for entry in data_list]
        temperaturas = [entry['dht11']['temperatura'] for entry in data_list]
        humedades = [entry['dht11']['humedad'] for entry in data_list]
        monoxido_carbono = [entry['gases']['monoxido_carbono'] for entry in data_list]
        gas_natural = [entry['gases']['gas_natural'] for entry in data_list]
        calidad_aire = [entry['gases']['calidad_aire'] for entry in data_list]

        # Crear el gráfico
        fig, axs = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
        axs[0].plot(timestamps, temperaturas, label='Temp (°C)', color='r')
        axs[0].set_ylabel('Temp (°C)')
        axs[0].legend()
        axs[0].grid(True)

        axs[1].plot(timestamps, humedades, label='Humedad (%)', color='b')
        axs[1].set_ylabel('Humedad (%)')
        axs[1].legend()
        axs[1].grid(True)

        axs[2].plot(timestamps, monoxido_carbono, label='CO', color='g')
        axs[2].set_ylabel('CO')
        axs[2].legend()
        axs[2].grid(True)

        axs[3].plot(timestamps, gas_natural, label='Gas Natural', color='y')
        axs[3].set_ylabel('Gas Natural')
        axs[3].legend()
        axs[3].grid(True)

        axs[4].plot(timestamps, calidad_aire, label='Calidad Aire', color='m')
        axs[4].set_ylabel('Calidad Aire')
        axs[4].legend()
        axs[4].grid(True)

        plt.xlabel('Tiempo')
        plt.tight_layout()

        # Guardar el gráfico en un archivo temporal
        fig.savefig('grafico_gases.png')

        # Enviar el gráfico a Telegram
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open('grafico_gases.png', 'rb'))

    except Exception as e:
        await update.message.reply_text(f"Error al generar el gráfico: {e}")

# Configuración del bot de Telegram
async def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Agregar manejadores
    application.add_handler(CommandHandler('datos', enviar_datos))
    application.add_handler(CommandHandler('grafico', enviar_grafico))

    # Iniciar el bot
    await application.initialize()
    await application.start_polling()
    await application.idle()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = GasMonitorApp()
    main_window.show()

    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(main())

    sys.exit(app.exec_())
