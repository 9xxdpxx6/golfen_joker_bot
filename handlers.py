import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import logger
from slots import interpret_slot_result
from database import init_db, update_player, reset_stats, get_stats

# Словарь с временем ожидания для каждой анимации
ANIMATION_DURATIONS = {
    "dart": 3,       
    "dice": 3.9,       
    "basketball": 4.4, 
    "football": 4.3,   
    "slot": 2.1, 
    "bowling": 3.5     
}

POINTS = {
    "dart": 10,
    "dice": 20,
    "basketball": 15,
    "football": 15,
    "bowling": 25,
    "slot": {64: 50, 8: 40, 16: 30, 32: 20}  # Очки за слоты
}

# Функция для старта бота
async def start(update: Update, context):
    logger.info("Команда /start получена")
    keyboard = [
        [InlineKeyboardButton("🎯 Дартс", callback_data="dart")],
        [InlineKeyboardButton("🎲 Кубики", callback_data="dice")],
        [InlineKeyboardButton("🏀 Баскетбол", callback_data="basketball")],
        [InlineKeyboardButton("⚽️ Футбол", callback_data="football")],
        [InlineKeyboardButton("🎰 Слоты", callback_data="slot")],  # Исправлено: "🎰" -> "🎰"
        [InlineKeyboardButton("🎳 Боулинг", callback_data="bowling")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери игру:", reply_markup=reply_markup)

# Обработчик выбора игры через кнопки или команды
async def handle_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_type: str):
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    query = update.callback_query if update.callback_query else None
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    username = update.message.from_user.username or "Unknown" if update.message else update.callback_query.from_user.username or "Unknown"

    if query:
        await query.answer()
        logger.info(f"Выбрана игра через кнопку: {game_type}")
    else:
        logger.info(f"Выбрана игра через команду: {game_type}")

    # Определяем тип анимированного эмодзи
    emoji_type = {
        "dart": "🎯",
        "dice": "🎲",
        "basketball": "🏀",
        "football": "⚽️",
        "slot": "🎰",
        "bowling": "🎳"
    }.get(game_type)

    # Логируем отправку анимированного эмодзи
    logger.info(f"Отправка анимированного эмодзи: {emoji_type}")
    
    # Отправляем анимированный эмодзи
    dice_message = await context.bot.send_dice(
        chat_id=chat_id,
        emoji=emoji_type,
        allow_sending_without_reply=True  # Обход flood control
    )

    # Определяем время ожидания для текущей анимации
    wait_time = ANIMATION_DURATIONS.get(game_type, 3)  # По умолчанию 3 секунды, если игра не найдена
    logger.info(f"Ожидание завершения анимации: {wait_time} секунд")
    await asyncio.sleep(wait_time)  # Задержка для завершения анимации

    # Получаем результат анимации из объекта dice_message
    result_1 = dice_message.dice.value
    logger.info(f"Первый результат кубика: {result_1}")

    # Если выбран кубик, отправляем второй кубик
    if game_type == "dice":
        # Отправляем второй анимированный кубик
        second_dice_message = await context.bot.send_dice(
            chat_id=chat_id,
            emoji=emoji_type,
            allow_sending_without_reply=True  # Обход flood control
        )

        # Ждём завершение анимации второго кубика
        wait_time_second = ANIMATION_DURATIONS.get(game_type, 3)  # По умолчанию 3 секунды
        logger.info(f"Ожидание завершения второго кубика: {wait_time_second} секунд")
        await asyncio.sleep(wait_time_second)

        # Получаем результат второго кубика
        result_2 = second_dice_message.dice.value
        logger.info(f"Второй результат кубика: {result_2}")

        # Проверяем, совпали ли результаты
        if result_1 == result_2:
            interpreted_result = f"🎲 Выпало: {result_1} и {result_2}. 🎉 Вы выиграли!"
            points = POINTS[game_type]
        else:
            interpreted_result = f"🎲 Выпало: {result_1} и {result_2}. ❌ Вы проиграли."
    else:
        # Для остальных игр интерпретируем результат стандартным способом
        if game_type == "dart":
            interpreted_result = "🎯 Попал в центр!" if result_1 == 6 else "❌ Не попал в центр."
            points = POINTS[game_type] if result_1 == 6 else 0
        elif game_type == "basketball":
            interpreted_result = "🏀 Попал в корзину!" if result_1 in [4, 5] else "❌ Не попал в корзину."
            points = POINTS[game_type] if result_1 in [4, 5] else 0
        elif game_type == "football":
            interpreted_result = "⚽️ Попал в ворота!" if result_1 in [3, 4, 5] else "❌ Не попал в ворота."
            points = POINTS[game_type] if result_1 in [3, 4, 5] else 0
        elif game_type == "bowling":
            interpreted_result = "🎳 Страйк! 🎉 Все кегли сбиты!" if result_1 == 6 else "❌ Неудача. Попробуйте еще раз."
            points = POINTS[game_type] if result_1 == 6 else 0
        elif game_type == "slot":
            slot_result = interpret_slot_result(result_1)
            interpreted_result = slot_result
            points = POINTS[game_type].get(result_1, 0)
        else:
            interpreted_result = f"Результат: {result_1}"

    # Отправляем сообщение с результатом
    if query:
        await query.edit_message_text(
            text=f"Вы выбрали игру {game_type.capitalize()}.\n{interpreted_result}"
        )
    else:
        await update.message.reply_text(
            text=f"Вы выбрали игру {game_type.capitalize()}.\n{interpreted_result}"
        )

    update_player(user_id, username, points)

# Обработчики команд
async def dart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_game(update, context, "dart")

async def dice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_game(update, context, "dice")

async def basketball_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_game(update, context, "basketball")

async def football_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_game(update, context, "football")

async def slot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_game(update, context, "slot")

async def bowling_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_game(update, context, "bowling")

# Обработчик выбора игры через кнопки
async def game_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    game_type = query.data
    await handle_game(update, context, game_type)

# Команды для статистики
async def stats_all(update: Update, context):
    stats = get_stats('all')
    message = "🏆 Статистика за всё время:\n"
    for idx, (username, points) in enumerate(stats, start=1):
        message += f"{idx}. @{username}: {points} очков\n"
    await update.message.reply_text(message)

async def stats_month(update: Update, context):
    stats = get_stats('month')
    message = "📅(30) Статистика за месяц:\n"
    for idx, (username, points) in enumerate(stats, start=1):
        message += f"{idx}. @{username}: {points} очков\n"
    await update.message.reply_text(message)

async def stats_week(update: Update, context):
    stats = get_stats('week')
    message = "📅(7) Статистика за неделю:\n"
    for idx, (username, points) in enumerate(stats, start=1):
        message += f"{idx}. @{username}: {points} очков\n"
    await update.message.reply_text(message)

async def stats_day(update: Update, context):
    stats = get_stats('day')
    message = "📅(1) Статистика за день:\n"
    for idx, (username, points) in enumerate(stats, start=1):
        message += f"{idx}. @{username}: {points} очков\n"
    await update.message.reply_text(message)