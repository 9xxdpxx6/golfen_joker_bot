from config import logger

# Стандартные стикеры для слотов
stickers = [
    0,  # Slot machine background
    1,  # Slot machine winning background
    2,  # Slot machine handle animation
    3,  # Left slot winning 7
    4,  # Left slot non-winning option 1 (слива)
    5,  # Left slot non-winning option 2
    6,  # Left slot non-winning option 3
    7,  # Left slot non-winning option 4
    8,  # Left slot spinning animation
    9,  # Center slot winning 7
    10,  # Center slot non-winning option 1 (бар)
    11,  # Center slot non-winning option 2
    12,  # Center slot non-winning option 3 (лимона)
    13,  # Center slot non-winning option 4
    14,  # Center slot spinning animation
    15,  # Right slot winning 7
    16,  # Right slot non-winning option 1 (бар)
    17,  # Right slot non-winning option 2 (слива)
    18,  # Right slot non-winning option 3 (лимона)
    19,  # Right slot non-winning option 4
    20,  # Right slot spinning animation
]

# Выигрышные комбинации и их коэффициенты
WINNING_COMBINATIONS = {
    (4, 10, 16): ("🍫🍫🍫", 2),  # Х2
    (6, 12, 18): ("🍋🍋🍋", 3),  # Х3
    (5, 11, 17): ("🍒🍒🍒", 4),  # Х4
    (7, 13, 19): ("7⃣7⃣7⃣", 7),  # Х7
}

# Функция для интерпретации результата для слотов
def interpret_slot_result(result):
    # Разделяем значение на три 2-битных поля
    left_slot = (result - 1) & 3  # Первые 2 бита
    center_slot = ((result - 1) >> 2) & 3  # Следующие 2 бита
    right_slot = ((result - 1) >> 4) & 3  # Последние 2 бита
    
    # Формируем комбинацию
    combination = (left_slot, center_slot, right_slot)
    
    # Проверяем, является ли комбинация выигрышной
    if combination in WINNING_COMBINATIONS:
        winning_symbol, multiplier = WINNING_COMBINATIONS[combination]
        return f"🎰 Выпало: {winning_symbol} 🎉 Вы выиграли x{multiplier}!"
    else:
        return "🎰 Не повезло. Попробуйте еще раз!"