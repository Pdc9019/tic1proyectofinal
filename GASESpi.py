import time
import json
import board
import adafruit_dht
import Adafruit_ADS1x15
import RPi.GPIO as GPIO
import subprocess

# Ejecutar el script para liberar el GPIO si hay conflictos
script_path = 'correct_sensor.sh'
result = subprocess.run([script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
if result.returncode != 0:
    print(f"Error al ejecutar el script: {result.stderr}")
else:
    print(f"Script ejecutado correctamente: {result.stdout}")

# Configuración GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Configuración de los pines del buzzer y LEDs
BUZZER_PIN = 4
LED_1 = 21  # LED Rojo para Monóxido de Carbono
LED_2 = 26  # LED verde para Gas Natural
LED_3 = 19  # LED azul para Calidad de Aire

GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(LED_1, GPIO.OUT)
GPIO.setup(LED_2, GPIO.OUT)
GPIO.setup(LED_3, GPIO.OUT)

# Configuración del sensor DHT11
dht_device = adafruit_dht.DHT11(board.D18)  # GPIO 18

# Configuración del ADC ADS1115
adc = Adafruit_ADS1x15.ADS1115()
GAIN = 1  # Ganancia para el ADS1115, puedes ajustarla si es necesario

# Archivo JSON para guardar los datos
json_filename = "gas_monitor_data.json"

# Funciones

def leer_dht11():
    for _ in range(3):  # Intentar leer hasta 3 veces
        try:
            temperatura = dht_device.temperature
            humedad = dht_device.humidity
            if temperatura is not None and humedad is not None:
                return {"temperatura": round(temperatura, 2), "humedad": round(humedad, 2)}
        except RuntimeError as error:
            print(f"Error de lectura DHT11: {error.args[0]}")
            time.sleep(2)  # Esperar un poco antes de reintentar
    return {"temperatura": None, "humedad": None}

def leer_gas():
    mq7_value = adc.read_adc(0, gain=GAIN)  # MQ-7 en canal A0
    mq5_value = adc.read_adc(1, gain=GAIN)  # MQ-5 en canal A1
    mq135_value = adc.read_adc(2, gain=GAIN)  # MQ-135 en canal A2
    return {
        "monoxido_carbono": mq7_value,
        "gas_natural": mq5_value,
        "calidad_aire": mq135_value
    }

def guardar_datos(datos):
    try:
        with open(json_filename, "a") as archivo:
            json.dump(datos, archivo)
            archivo.write("\n")
    except Exception as e:
        print(f"Error guardando los datos: {e}")

def activar_alarma(led_pin):
    GPIO.output(led_pin, GPIO.HIGH)
    for _ in range(5):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(0.2)
    GPIO.output(led_pin, GPIO.LOW)

# Loop principal
try:
    while True:
        # Leer sensores
        datos_dht11 = leer_dht11()
        datos_gas = leer_gas()

        # Combinar los datos de todos los sensores
        datos_totales = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dht11": datos_dht11,
            "gases": datos_gas
        }

        # Guardar los datos en el archivo JSON
        guardar_datos(datos_totales)

        # Mostrar los datos en la consola para verificar
        print(datos_totales)

        # Lógica de alarmas
        if datos_gas["monoxido_carbono"] > 5000:  # Umbral para Monóxido de Carbono
            activar_alarma(LED_1)
        if datos_gas["gas_natural"] > 6000:  # Umbral para Gas Natural
            activar_alarma(LED_2)
        if datos_gas["calidad_saire"] > 3500:  # Umbral para Calidad de Aire
            activar_alarma(LED_3)

        # Esperar antes de la próxima lectura
        time.sleep(10)

except KeyboardInterrupt:
    print("\nPrograma detenido por el usuario.")
finally:
    GPIO.cleanup()  # Limpiar la configuración GPIO
