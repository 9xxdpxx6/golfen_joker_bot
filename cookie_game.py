import random
from dataclasses import dataclass
from typing import List, Dict, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

@dataclass
class CookieGame:
    size: int = 5
    bomb_count: int = 7  # Количество бомб на поле
    base_reward: int = 500  # Увеличиваем базовую награду
    field: List[List[bool]] = None  # True = бомба, False = приз
    opened: List[List[bool]] = None  # True = открыто, False = закрыто
    current_reward: int = 0
    game_over: bool = False
    player_id: int = None  # ID игрока, который начал игру

    def __post_init__(self):
        self.field = [[False for _ in range(self.size)] for _ in range(self.size)]
        self.opened = [[False for _ in range(self.size)] for _ in range(self.size)]
        self._place_bombs()
        
    def _place_bombs(self):
        # Размещаем бомбы случайным образом
        bombs_placed = 0
        while bombs_placed < self.bomb_count:
            x, y = random.randint(0, self.size-1), random.randint(0, self.size-1)
            if not self.field[y][x]:
                self.field[y][x] = True
                bombs_placed += 1

    def open_cell(self, x: int, y: int) -> Tuple[bool, int]:
        """Открывает ячейку. Возвращает (is_bomb, reward)"""
        if self.opened[y][x] or self.game_over:
            return False, self.current_reward
        
        self.opened[y][x] = True
        if self.field[y][x]:  # Бомба
            self.game_over = True
            return True, 0
        
        self.current_reward += self.base_reward
        return False, self.current_reward

    def get_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = []
        for y in range(self.size):
            row = []
            for x in range(self.size):
                if self.opened[y][x]:  # Уже открытая ячейка
                    text = "💣" if self.field[y][x] else "🍪"
                elif self.game_over and self.field[y][x]:  # Неоткрытая бомба при game_over
                    text = "💣"
                elif self.game_over:  # Неоткрытая печенька при game_over
                    text = "🥠"
                else:  # Закрытая ячейка в процессе игры
                    text = "⬜️"
                row.append(InlineKeyboardButton(text, callback_data=f"cookie_{x}_{y}"))
            keyboard.append(row)
        
        if not self.game_over:
            keyboard.append([InlineKeyboardButton(
                f"💰 Забрать приз ({self.current_reward} токенов)", 
                callback_data="cookie_claim"
            )])
        
        return InlineKeyboardMarkup(keyboard)

# Хранилище активных игр: (chat_id, message_id) -> game
active_games: Dict[Tuple[int, int], CookieGame] = {}

def start_game(chat_id: int, message_id: int, player_id: int) -> CookieGame:
    game = CookieGame(player_id=player_id)
    active_games[(chat_id, message_id)] = game
    return game

def get_game(chat_id: int, message_id: int) -> CookieGame:
    return active_games.get((chat_id, message_id))

def end_game(chat_id: int, message_id: int):
    if (chat_id, message_id) in active_games:
        del active_games[(chat_id, message_id)] 