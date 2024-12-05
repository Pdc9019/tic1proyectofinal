import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configurar el logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Token del bot de Telegram 
TOKEN = "tokentokentokentokentoken"

# Definir el comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enviar mensaje de bienvenida al usar /start"""
    await update.message.reply_text("Hola, estoy listo para enviar datos")

# Definir el comando /grafico para enviar el gráfico guardado
async def enviar_grafico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Leer el gráfico previamente generado y guardado como 'grafico_gases.png'
        with open('grafico_gases.png', 'rb') as grafico:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=grafico)
    except FileNotFoundError:
        await update.message.reply_text("No se encontró el gráfico. Por favor, asegúrate de que el monitoreo esté generando el gráfico correctamente.")

async def main():
    # Crear la aplicación y agregar manejadores
    application = ApplicationBuilder().token(TOKEN).build()

    # Manejadores de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("grafico", enviar_grafico))

    # Iniciar el bot sin utilizar asyncio.run() para evitar conflictos de bucle de eventos
    await application.initialize()
    await application.start()
    print("Bot is running. Press Ctrl+C to stop.")
    await application.updater.start_polling()

    # A la espera de una señal para terminar
    try:
        await asyncio.Future()  # Se mantiene el bucle hasta que se interrumpa manualmente
    except (KeyboardInterrupt, SystemExit):
        print("Stopping bot...")
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main(), debug=True)
