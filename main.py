from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
)
from handlers import (
    start,
    game_choice,
    dart_command,
    dice_command,
    basketball_command,
    football_command,
    slot_command,
    bowling_command,
    stats_all,
    stats_month,
    stats_week,
    stats_day,
)
from config import read_token_from_file
from telegram import Update
from database import init_db

# Основная функция запуска бота
def main():
    token = read_token_from_file('env.txt')
    if not token:
        print("Токен не найден в файле env.txt")
        return

    init_db()

    application = ApplicationBuilder().token(token).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("dart", dart_command))
    application.add_handler(CommandHandler("dice", dice_command))
    application.add_handler(CommandHandler("basketball", basketball_command))
    application.add_handler(CommandHandler("football", football_command))
    application.add_handler(CommandHandler("slot", slot_command))
    application.add_handler(CommandHandler("bowling", bowling_command))
    application.add_handler(CommandHandler("stats_all", stats_all))
    application.add_handler(CommandHandler("stats_month", stats_month))
    application.add_handler(CommandHandler("stats_week", stats_week))
    application.add_handler(CommandHandler("stats_day", stats_day))

    # Регистрация обработчика выбора игры через кнопки
    application.add_handler(CallbackQueryHandler(game_choice))

    # Логирование всех обновлений
    async def log_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Получено обновление: {update}")

    application.add_handler(MessageHandler(None, log_updates))

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()