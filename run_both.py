from multiprocessing import Process
import subprocess

def run_monitor():
    subprocess.run(["python", "C:\\Users\\benja\\Desktop\\PROYECTOFINAL\\GASESpc2.py"])

def run_telegram():
    subprocess.run(["python", "C:\\Users\\benja\\Desktop\\PROYECTOFINAL\\Telegram.py"])

if __name__ == "__main__":
    # Crear procesos independientes para cada script
    monitor_process = Process(target=run_monitor)
    telegram_process = Process(target=run_telegram)

    # Iniciar ambos procesos
    monitor_process.start()
    telegram_process.start()

    # Esperar que ambos procesos terminen (opcional)
    monitor_process.join()
    telegram_process.join()
