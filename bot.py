# bot.py
import os
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from wakeonlan import send_magic_packet

TOKEN = os.environ.get('8650718107:AAHVYiqhrgBjVqrebaHEWEK0R615Nmm8TZE')
MAC = os.environ.get('00:E0:2F:1D:4D:34')  # Пример: "AA:BB:CC:DD:EE:FF"
BROADCAST = os.environ.get('192.168.1.2', '255.255.255.255')  # По умолчанию широковещательный

if not TOKEN or not MAC:
    raise SystemExit("Set TELEGRAM_BOT_TOKEN and TARGET_MAC environment variables")

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Бот готов. Используй /wake чтобы включить ПК.")

def wake(update: Update, context: CallbackContext):
    try:
        send_magic_packet(MAC, ip_address=BROADCAST)
        update.message.reply_text(f"Отправлен WoL пакет на {MAC}")
    except Exception as e:
        update.message.reply_text(f"Ошибка при отправке WoL: {e}")

def shutdown(update: Update, context: CallbackContext):
    update.message.reply_text("Команда выключения не реализована в этом примере.")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("wake", wake))
    dp.add_handler(CommandHandler("shutdown", shutdown))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
