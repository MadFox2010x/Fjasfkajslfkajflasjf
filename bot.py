import os
import asyncio
import platform
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from wakeonlan import send_magic_packet

# --- НАСТРОЙКИ ---
TOKEN = "8650718107:AAHVYiqhrgBjVqrebaHEWEK0R615Nmm8TZE"
MAC_ADDRESS = "00:E0:2F:1D:4D:34"
BROADCAST_IP = "192.168.1.255"
CORRECT_PASSWORD = "9506"

# Данные для отправки ПК в сон (пример через SSH)
PC_IP = "192.168.1.50"  # Локальный IP вашего ПК
SSH_USER = "your_username"
# Команда сна для Linux: "systemctl suspend"
# Команда сна для Windows (через SSH): "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"
SHUTDOWN_CMD = f"ssh {SSH_USER}@{PC_IP} 'systemctl suspend'" 

# Состояния пользователя
USER_STATES = {} # True если авторизован

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def delete_message_delayed(message, delay=2):
    """Удаляет сообщение через указанное количество секунд."""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

def is_pc_online(ip):
    """Проверяет, включен ли ПК с помощью ping."""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', ip]
    return os.system(' '.join(command)) == 0

def get_menu_keyboard(is_online):
    """Формирует кнопку в зависимости от статуса ПК."""
    text = "🌙 Перевести в сон" if is_online else "🔌 Включить (WoL)"
    callback_data = "to_sleep" if is_online else "to_wake"
    
    keyboard = [[InlineKeyboardButton(text, callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)

async def build_menu_text():
    """Формирует текст главного меню."""
    online = is_pc_online(PC_IP)
    status = "🟢 Включен" if online else "🔴 Выключен (В спящем режиме)"
    return f"🖥 **Статус вашего компьютера:** {status}", online

# --- ОБРАБОТЧИКИ КОМАНД ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сразу удаляем команду /start от пользователя
    await update.message.delete()
    
    user_id = update.effective_user.id
    USER_STATES[user_id] = False # Сбрасываем авторизацию
    
    # Отправляем сообщение с запросом пароля
    msg = await update.effective_chat.send_message("🔑 Введите 4-значный код доступа:")
    # Запоминаем ID главного сообщения меню
    context.user_data['menu_msg_id'] = msg.message_id

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    menu_msg_id = context.user_data.get('menu_msg_id')

    # Если пользователь еще не авторизован
    if not USER_STATES.get(user_id, False):
        if text == CORRECT_PASSWORD:
            USER_STATES[user_id] = True
            # Удаляем сообщение пользователя мгновенно
            await update.message.delete()
            
            if menu_msg_id:
                # Переключаем интерфейс на меню управления в том же сообщении
                text_menu, online = await build_menu_text()
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=menu_msg_id,
                    text=text_menu,
                    reply_markup=get_menu_keyboard(online),
                    parse_mode="Markdown"
                )
        else:
            # Если пароль неверный
            await update.message.delete() # Удаляем ввод пользователя
            error_msg = await update.effective_chat.send_message("❌ Неверный пароль!")
            # Удаляем уведомление об ошибке через 2 секунды
            asyncio.create_task(delete_message_delayed(error_msg, 2))
    else:
        # Если авторизован, но пишет всякий мусор в чат — жестко удаляем
        await update.message.delete()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Убираем "часики" с кнопки
    
    user_id = update.effective_user.id
    if not USER_STATES.get(user_id, False):
        return

    action = query.data

    if action == "to_wake":
        try:
            send_magic_packet(MAC_ADDRESS, ip_address=BROADCAST_IP)
            # Небольшая пауза, чтобы ПК успел ответить на ping (опционально)
            await asyncio.sleep(3) 
        except Exception as e:
            print(f"Ошибка WoL: {e}")
            
    elif action == "to_sleep":
        # Выполняем системную команду для отправки в сон
        os.system(SHUTDOWN_CMD)
        await asyncio.sleep(3)

    # Обновляем это же сообщение
    text_menu, online = await build_menu_text()
    await query.edit_message_text(
        text=text_menu,
        reply_markup=get_menu_keyboard(online),
        parse_mode="Markdown"
    )

# --- ЗАПУСК БОТА ---

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    # Ловим текстовые сообщения (и пароль, и флуд)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
