import paramiko
import json
import matplotlib.pyplot as plt
import datetime
from PyQt5 import QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import sys
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

class GasMonitorApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Gases")
        self.setGeometry(100, 100, 1200, 800)

        # Widget principal
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout principal dividido en dos columnas
        self.main_layout = QtWidgets.QHBoxLayout(self.central_widget)

        # Layout izquierdo para los valores numéricos
        self.left_layout = QtWidgets.QVBoxLayout()

        # Grupo para mostrar lecturas numéricas
        self.sensorGroup = QtWidgets.QGroupBox("Lecturas de Sensores")
        self.sensorLayout = QtWidgets.QVBoxLayout()

        # LCDs para mostrar valores de sensores
        self.n1Temperatura = QtWidgets.QLCDNumber()
        self.n1Temperatura.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.n2Humedad = QtWidgets.QLCDNumber()
        self.n2Humedad.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.n3GasNatural = QtWidgets.QLCDNumber()
        self.n3GasNatural.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.n4MonoxidoCarbono = QtWidgets.QLCDNumber()
        self.n4MonoxidoCarbono.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.n5CalidadAire = QtWidgets.QLCDNumber()
        self.n5CalidadAire.setSegmentStyle(QtWidgets.QLCDNumber.Flat)

        # Añadir los LCDs al layout del grupo
        self.sensorLayout.addWidget(QtWidgets.QLabel("Temperatura (°C)"))
        self.sensorLayout.addWidget(self.n1Temperatura)
        self.sensorLayout.addWidget(QtWidgets.QLabel("Humedad (%)"))
        self.sensorLayout.addWidget(self.n2Humedad)
        self.sensorLayout.addWidget(QtWidgets.QLabel("Gas Natural (ppm)"))
        self.sensorLayout.addWidget(self.n3GasNatural)
        self.sensorLayout.addWidget(QtWidgets.QLabel("Monóxido de Carbono (ppm)"))
        self.sensorLayout.addWidget(self.n4MonoxidoCarbono)
        self.sensorLayout.addWidget(QtWidgets.QLabel("Calidad de Aire (ppm)"))
        self.sensorLayout.addWidget(self.n5CalidadAire)

        self.sensorGroup.setLayout(self.sensorLayout)
        self.left_layout.addWidget(self.sensorGroup)

        # Añadir la sección de la izquierda al layout principal
        self.main_layout.addLayout(self.left_layout)

        # Área de gráficos en la sección derecha (ocupando 3/4 del espacio)
        self.figure, self.axs = plt.subplots(5, 1, figsize=(10, 15), sharex=True)
        self.canvas = FigureCanvas(self.figure)
        self.main_layout.addWidget(self.canvas, stretch=3)

        # Botón para actualizar los datos manualmente
        self.updateButton = QtWidgets.QPushButton("Actualizar Datos")
        self.updateButton.clicked.connect(self.actualizar_datos)
        self.left_layout.addWidget(self.updateButton)

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

            # Actualizar los valores de los LCDs
            if data_list:
                ultimo_dato = data_list[-1]

                self.n1Temperatura.display(ultimo_dato['dht11']['temperatura'])
                self.n2Humedad.display(ultimo_dato['dht11']['humedad'])
                self.n3GasNatural.display(ultimo_dato['gases']['gas_natural'])
                self.n4MonoxidoCarbono.display(ultimo_dato['gases']['monoxido_carbono'])
                self.n5CalidadAire.display(ultimo_dato['gases']['calidad_aire'])

                # Cambiar el color de los LCDs según los límites de advertencia
                self.cambiar_color_lcd(self.n3GasNatural, ultimo_dato['gases']['gas_natural'], 6000)
                self.cambiar_color_lcd(self.n4MonoxidoCarbono, ultimo_dato['gases']['monoxido_carbono'], 5000)
                self.cambiar_color_lcd(self.n5CalidadAire, ultimo_dato['gases']['calidad_aire'], 3500)

                # Actualizar gráficos
                self.graficar_datos(data_list)

        except Exception as e:
            print(f"Error al conectarse a la Raspberry Pi o leer el archivo: {e}")

    def cambiar_color_lcd(self, lcd, valor, limite):
        """Cambia el color del LCD si el valor supera el límite."""
        if valor > limite:
            lcd.setStyleSheet("background-color: red;")
        else:
            lcd.setStyleSheet("background-color: white;")

    def graficar_datos(self, data_list):
        # Limpiar los ejes antes de volver a dibujar
        for ax in self.axs:
            ax.clear()

        if not data_list:
            print("No hay datos disponibles para graficar.")
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

        # Guardar el gráfico para futuras referencias
        self.figure.savefig('grafico_gases.png')

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = GasMonitorApp()
    main_window.show()
    sys.exit(app.exec_())
