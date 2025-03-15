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
    stats_hour,
    claim_tokens_command,
    cookie_command,
    cookie_button,
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

    # Регистрация обработчиков в правильном порядке
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
    application.add_handler(CommandHandler("stats_hour", stats_hour))
    application.add_handler(CommandHandler("free_tokens", claim_tokens_command))
    application.add_handler(CommandHandler("cookie", cookie_command))

    # Сначала регистрируем обработчик для cookie
    application.add_handler(CallbackQueryHandler(cookie_button, pattern="^cookie_"))
    # Затем регистрируем обработчик для остальных игр с уточненным паттерном
    application.add_handler(CallbackQueryHandler(game_choice, pattern="^(dart|dice|basketball|football|slot|bowling)$"))

    # Логирование всех обновлений
    async def log_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Получено обновление: {update}")

    application.add_handler(MessageHandler(None, log_updates))

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()