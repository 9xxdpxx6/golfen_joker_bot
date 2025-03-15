import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from datetime import datetime, timedelta
from collections import defaultdict

from config import logger
from database import init_db, update_player, get_stats, get_user_tokens, update_user_tokens, ensure_user_exists
from cookie_game import start_game, get_game, end_game

# Словарь с временем ожидания для каждой анимации
ANIMATION_DURATIONS = {
    "dart": 4.0,       
    "dice": 3.4,     # Уменьшаем время ожидания для кубиков
    "basketball": 4.8, 
    "football": 4.7,   
    "slot": 2.5, 
    "bowling": 4.0     
}

POINTS = {
    "dart": 1200,      # Попадание в центр
    "dice": 600,       # Базовое значение для кубиков (будет умножаться на выпавшее число)
    "basketball": 400, # Попадание в корзину
    "football": 300,   # Гол
    "bowling": 600,    # Страйк
    "slot": {
        1: ("🍫🍫🍫", 2000),  # Три бара
        43: ("🍋🍋🍋", 3000), # Три лимона
        22: ("🍒🍒🍒", 4000), # Три вишни
        64: ("7⃣7⃣7⃣", 7000)  # 777
    }
}
    
# Словарь для хранения времени последней игры для каждого пользователя и типа игры
# Формат: {user_id: {game_type: timestamp}}
last_game_timestamps = defaultdict(lambda: defaultdict(float))
COOLDOWN_SECONDS = 10

# Константа для ставки
BET_AMOUNT = 300

# Словарь для хранения времени последнего получения токенов
last_token_claims = defaultdict(float)
TOKEN_COOLDOWN = 7200  # 2 часа в секундах

async def check_cooldown(user_id: int, game_type: str) -> bool:
    """
    Проверяет, прошло ли достаточно времени с последней игры данного типа
    Возвращает True если можно играть, False если нужно подождать
    """
    last_timestamp = last_game_timestamps[user_id][game_type]
    if last_timestamp == 0:
        return True
        
    time_passed = datetime.now().timestamp() - last_timestamp
    return time_passed >= COOLDOWN_SECONDS

async def check_token_cooldown(user_id: int) -> tuple[bool, int]:
    """
    Проверяет, прошло ли достаточно времени с последнего получения токенов
    Возвращает (можно_получить, оставшееся_время)
    """
    last_claim = last_token_claims[user_id]
    if last_claim == 0:
        return True, 0
        
    time_passed = datetime.now().timestamp() - last_claim
    if time_passed >= TOKEN_COOLDOWN:
        return True, 0
    else:
        remaining = TOKEN_COOLDOWN - time_passed
        return False, int(remaining)

# Функция для старта бота
async def start(update: Update, context):
    logger.info("Команда /start получена")
    keyboard = [
        [InlineKeyboardButton("🎯 Дартс", callback_data="dart")],
        [InlineKeyboardButton("🎲 Кубики", callback_data="dice")],
        [InlineKeyboardButton("🏀 Баскетбол", callback_data="basketball")],
        [InlineKeyboardButton("⚽️ Футбол", callback_data="football")],
        [InlineKeyboardButton("🎰 Слоты", callback_data="slot")], 
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

    # Проверяем наличие токенов
    current_tokens = get_user_tokens(user_id)
    if current_tokens < BET_AMOUNT:
        message = f"❌ Недостаточно токенов! Необходимо: {BET_AMOUNT}, у вас: {current_tokens}\nИспользуйте команду /tokens чтобы получить токены"
        if query:
            await query.answer(text=message, show_alert=True)
        else:
            await update.message.reply_text(message)
        return

    # Списываем ставку
    update_user_tokens(user_id, -BET_AMOUNT)

    # Проверяем кулдаун
    if not await check_cooldown(user_id, game_type):
        remaining_time = COOLDOWN_SECONDS - (datetime.now().timestamp() - last_game_timestamps[user_id][game_type])
        cooldown_message = f"⏳ Подождите {int(remaining_time)} секунд перед следующей игрой в {game_type.capitalize()}"
        if query:
            await query.answer(text=cooldown_message, show_alert=True)
            return
        else:
            await update.message.reply_text(cooldown_message)
            return

    if query:
        await query.answer()
        reply_to_message_id = query.message.message_id
    else:
        reply_to_message_id = update.message.message_id

    emoji_type = {
        "dart": "🎯",
        "dice": "🎲",
        "basketball": "🏀",
        "football": "⚽️",
        "slot": "🎰",
        "bowling": "🎳"
    }.get(game_type)

    async def process_game_result():
        nonlocal points, interpreted_result
        # Ждём завершения анимации
        wait_time = ANIMATION_DURATIONS.get(game_type, 3) + 0.2
        await asyncio.sleep(wait_time)

        try:
            if game_type == "dice":
                result_1 = first_dice.dice.value
                result_2 = second_dice.dice.value
                if result_1 == result_2:
                    multiplier = result_1
                    points = POINTS[game_type] * multiplier
                    interpreted_result = f"🎲 Выпало: {result_1} и {result_2}. 🎉 Вы выиграли! (x{multiplier})"
                else:
                    interpreted_result = f"🎲 Выпало: {result_1} и {result_2}. ❌ Вы проиграли."
                    points = 0
            else:
                result_1 = dice_message.dice.value
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
                    slot_result = POINTS[game_type].get(result_1)
                    if slot_result:
                        winning_symbol, points = slot_result
                        interpreted_result = f"🎰 Выпало: {winning_symbol} 🎉 Вы выиграли!"
                    else:
                        interpreted_result = "❌ Вы проиграли."
                        points = 0

            # Отправляем сообщение с результатом
            if query:
                message_text = f"Вы выбрали игру {game_type.capitalize()}.\n{interpreted_result}"
                if points > 0:
                    message_text += f"\n💰 Выигрыш: {points} токенов"
                await query.edit_message_text(text=message_text)
            else:
                message_text = f"Вы выбрали игру {game_type.capitalize()}.\n{interpreted_result}"
                if points > 0:
                    message_text += f" Выигрыш: {points} токенов"
                await update.message.reply_text(text=message_text)

            # Обновляем статистику игрока
            update_player(user_id, username, points, chat_id, game_type)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке результата: {e}")

    # Отправляем эмодзи сразу
    points = 0
    interpreted_result = ""
    
    if game_type == "dice":
        first_dice = await context.bot.send_dice(chat_id=chat_id, emoji=emoji_type)
        second_dice = await context.bot.send_dice(chat_id=chat_id, emoji=emoji_type)
    else:
        dice_message = await context.bot.send_dice(chat_id=chat_id, emoji=emoji_type)

    # Запускаем обработку результата асинхронно без ожидания завершения
    asyncio.create_task(process_game_result())

    # Обновляем время последней игры
    last_game_timestamps[user_id][game_type] = datetime.now().timestamp()

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
    chat_id = update.message.chat_id
    stats = get_stats('all', chat_id)
    message = "🏆 Статистика за всё время:\n"
    for idx, (username, points) in enumerate(stats, start=1):
        message += f"{idx}. @{username}: {points} очков\n"
    await update.message.reply_text(message)

async def stats_month(update: Update, context):
    chat_id = update.message.chat_id
    stats = get_stats('month', chat_id)
    message = "📅(30) Статистика за месяц:\n"
    for idx, (username, points) in enumerate(stats, start=1):
        message += f"{idx}. @{username}: {points} очков\n"
    await update.message.reply_text(message)

async def stats_week(update: Update, context):
    chat_id = update.message.chat_id
    stats = get_stats('week', chat_id)
    message = "📅(7) Статистика за неделю:\n"
    for idx, (username, points) in enumerate(stats, start=1):
        message += f"{idx}. @{username}: {points} очков\n"
    await update.message.reply_text(message)

async def stats_day(update: Update, context):
    chat_id = update.message.chat_id
    stats = get_stats('day', chat_id)
    message = "📅(1) Статистика за день:\n"
    for idx, (username, points) in enumerate(stats, start=1):
        message += f"{idx}. @{username}: {points} очков\n"
    await update.message.reply_text(message)

async def stats_hour(update: Update, context):
    chat_id = update.message.chat_id
    stats = get_stats('hour', chat_id)
    message = "⏰ Статистика за час:\n"
    for idx, (username, points) in enumerate(stats, start=1):
        message += f"{idx}. @{username}: {points} очков\n"
    await update.message.reply_text(message)

async def claim_tokens_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"
    
    can_claim, remaining_seconds = await check_token_cooldown(user_id)
    
    if can_claim:
        ensure_user_exists(user_id, username)
        update_user_tokens(user_id, 10000)
        last_token_claims[user_id] = datetime.now().timestamp()
        await update.message.reply_text("💰 Вы получили 10000 токенов!")
    else:
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        await update.message.reply_text(
            f"⏳ Следующие токены будут доступны через {hours}ч {minutes}мин"
        )

async def cookie_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    # Проверяем наличие токенов
    current_tokens = get_user_tokens(user_id)
    if current_tokens < BET_AMOUNT:
        await update.message.reply_text(
            f"❌ Недостаточно токенов! Необходимо: {BET_AMOUNT}, у вас: {current_tokens}\n"
            "Используйте команду /free_tokens чтобы получить токены"
        )
        return

    # Списываем ставку
    update_user_tokens(user_id, -BET_AMOUNT)
    
    # Отправляем сообщение и сохраняем его ID
    message = await update.message.reply_text(
        "🍪 Игра 'Печенька' началась!\nНайдите печеньки и не нарвитесь на бомбы!"
    )
    
    # Начинаем новую игру с сохранением message_id
    game = start_game(chat_id, message.message_id, user_id)
    
    # Обновляем сообщение с клавиатурой
    await message.edit_text(
        f"🍪 Игра 'Печенька' началась!\nИгрок: @{update.message.from_user.username}\nНайдите печеньки и не нарвитесь на бомбы!",
        reply_markup=game.get_keyboard()
    )

async def cookie_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    user_id = query.from_user.id
    
    game = get_game(chat_id, message_id)
    
    if not game:
        await query.edit_message_text(
            "Игра не найдена! Начните новую игру командой /cookie",
            reply_markup=None
        )
        return

    # Проверяем, что кнопку нажимает тот же игрок
    if game.player_id != user_id:
        await query.answer("Эта игра начата другим игроком!")
        return

    data = query.data
    if data == "cookie_claim":
        reward = game.current_reward
        if reward > 0:
            update_user_tokens(user_id, reward)
            await query.edit_message_text(
                f"🎉 Поздравляем!\nИгрок @{query.from_user.username} забрал выигрыш: {reward} токенов!",
                reply_markup=None
            )
            end_game(chat_id, message_id)
        else:
            await query.answer("Нечего забирать! Откройте хотя бы одну печеньку.")
            return
    else:
        _, x, y = data.split('_')
        x, y = int(x), int(y)
        is_bomb, reward = game.open_cell(x, y)
        
        if is_bomb:
            await query.edit_message_text(
                f"💥 БУМ! Игрок @{query.from_user.username} попался на бомбу! Игра окончена!",
                reply_markup=game.get_keyboard()
            )
            end_game(chat_id, message_id)
        else:
            await query.edit_message_text(
                f"🍪 Игрок: @{query.from_user.username}\nНайдена печенька!\nТекущий выигрыш: {reward} токенов\nПродолжайте или заберите приз!",
                reply_markup=game.get_keyboard()
            )