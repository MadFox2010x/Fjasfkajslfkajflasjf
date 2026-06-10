# main.py
import os
import asyncio
import platform
from wakeonlan import send_magic_packet
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Настройки через переменные окружения
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MAC_ADDRESS = os.environ.get("TARGET_MAC")  # "00:E0:2F:1D:4D:34"
BROADCAST_IP = os.environ.get("BROADCAST_IP", "255.255.255.255")
CORRECT_PASSWORD = os.environ.get("ACCESS_CODE", "9506")
PC_IP = os.environ.get("PC_IP", "192.168.1.50")
SSH_USER = os.environ.get("SSH_USER", "your_username")
SHUTDOWN_CMD = f"ssh {SSH_USER}@{PC_IP} 'systemctl suspend'"

if not TOKEN or not MAC_ADDRESS:
    raise SystemExit("Set TELEGRAM_BOT_TOKEN and TARGET_MAC environment variables")

USER_STATES = {}

async def delete_message_delayed(message, delay=2):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

def is_pc_online(ip):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', ip]
    return os.system(' '.join(command)) == 0

def get_menu_keyboard(is_online):
    text = "🌙 Перевести в сон" if is_online else "🔌 Включить (WoL)"
    callback_data = "to_sleep" if is_online else "to_wake"
    keyboard = [[InlineKeyboardButton(text, callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)

async def build_menu_text():
    online = is_pc_online(PC_IP)
    status = "🟢 Включен" if online else "🔴 Выключен (В спящем режиме)"
    return f"🖥 **Статус вашего компьютера:** {status}", online

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()
    user_id = update.effective_user.id
    USER_STATES[user_id] = False
    msg = await update.effective_chat.send_message("🔑 Введите 4-значный код доступа:")
    context.user_data['menu_msg_id'] = msg.message_id

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    menu_msg_id = context.user_data.get('menu_msg_id')
    if not USER_STATES.get(user_id, False):
        if text == CORRECT_PASSWORD:
            USER_STATES[user_id] = True
            await update.message.delete()
            if menu_msg_id:
                text_menu, online = await build_menu_text()
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=menu_msg_id,
                    text=text_menu,
                    reply_markup=get_menu_keyboard(online),
                    parse_mode="Markdown"
                )
        else:
            await update.message.delete()
            error_msg = await update.effective_chat.send_message("❌ Неверный пароль!")
            asyncio.create_task(delete_message_delayed(error_msg, 2))
    else:
        await update.message.delete()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not USER_STATES.get(user_id, False):
        return
    action = query.data
    if action == "to_wake":
        try:
            send_magic_packet(MAC_ADDRESS, ip_address=BROADCAST_IP)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Ошибка WoL: {e}")
    elif action == "to_sleep":
        os.system(SHUTDOWN_CMD)
        await asyncio.sleep(3)
    text_menu, online = await build_menu_text()
    await query.edit_message_text(
        text=text_menu,
        reply_markup=get_menu_keyboard(online),
        parse_mode="Markdown"
    )

# --- Запуск бота ---
async def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
