# main.py
import os
import platform
from wakeonlan import send_magic_packet
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

# Настройки через переменные окружения
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MAC_ADDRESS = os.environ.get("TARGET_MAC")  # "00:E0:2F-1D-4D-34"
BROADCAST_IP = os.environ.get("BROADCAST_IP", "255.255.255.255")
CORRECT_PASSWORD = os.environ.get("ACCESS_CODE", "9506")
PC_IP = os.environ.get("PC_IP", "192.168.1.50")
SSH_USER = os.environ.get("SSH_USER", "your_username")
SHUTDOWN_CMD = f"ssh {SSH_USER}@{PC_IP} 'systemctl suspend'"

if not TOKEN or not MAC_ADDRESS:
    raise SystemExit("Set TELEGRAM_BOT_TOKEN and TARGET_MAC environment variables")

USER_STATES = {}

def is_pc_online(ip):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', ip]
    return os.system(' '.join(command)) == 0

def get_menu_keyboard(is_online):
    text = "🌙 Перевести в сон" if is_online else "🔌 Включить (WoL)"
    callback_data = "to_sleep" if is_online else "to_wake"
    keyboard = [[InlineKeyboardButton(text, callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)

def build_menu_text():
    online = is_pc_online(PC_IP)
    status = "🟢 Включен" if online else "🔴 Выключен (В спящем режиме)"
    return f"🖥 Статус вашего компьютера: {status}", online

def start(update, context):
    update.message.delete()
    user_id = update.effective_user.id
    USER_STATES[user_id] = False
    msg = update.effective_chat.send_message("🔑 Введите 4-значный код доступа:")
    context.user_data['menu_msg_id'] = msg.message_id

def handle_message(update, context):
    user_id = update.effective_user.id
    text = update.message.text
    menu_msg_id = context.user_data.get('menu_msg_id')
    if not USER_STATES.get(user_id, False):
        if text == CORRECT_PASSWORD:
            USER_STATES[user_id] = True
            update.message.delete()
            if menu_msg_id:
                text_menu, online = build_menu_text()
                context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=menu_msg_id,
                    text=text_menu,
                    reply_markup=get_menu_keyboard(online),
                    parse_mode="Markdown"
                )
        else:
            update.message.delete()
            error_msg = update.effective_chat.send_message("❌ Неверный пароль!")
            context.job_queue.run_once(lambda c: error_msg.delete(), 2)
    else:
        update.message.delete()

def button_handler(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    if not USER_STATES.get(user_id, False):
        return
    action = query.data
    if action == "to_wake":
        try:
            send_magic_packet(MAC_ADDRESS, ip_address=BROADCAST_IP)
        except Exception as e:
            print(f"Ошибка WoL: {e}")
    elif action == "to_sleep":
        os.system(SHUTDOWN_CMD)
    text_menu, online = build_menu_text()
    query.edit_message_text(
        text=text_menu,
        reply_markup=get_menu_keyboard(online),
        parse_mode="Markdown"
    )

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    print("Бот запущен...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
