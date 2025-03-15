import sqlite3
from datetime import datetime, timedelta

# Подключение к базе данных
conn = sqlite3.connect('stats.sqlite', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    # Включаем поддержку внешних ключей
    cursor.execute('PRAGMA foreign_keys = ON')
    
    # Создаем таблицы в правильном порядке
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            tokens INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            chat_name TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            game_name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id INTEGER,
            game_id TEXT,
            points INTEGER,
            played_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id),
            FOREIGN KEY (game_id) REFERENCES games(game_id)
        )
    ''')

    # Проверяем, есть ли колонка tokens в таблице users
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'tokens' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN tokens INTEGER DEFAULT 0')

    # Заполняем справочник игр, игнорируя дубликаты
    games = [
        ('dart', 'Дартс'),
        ('dice', 'Кубики'),
        ('basketball', 'Баскетбол'),
        ('football', 'Футбол'),
        ('slot', 'Слоты'),
        ('bowling', 'Боулинг')
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO games (game_id, game_name) 
        VALUES (?, ?)
    ''', games)
    conn.commit()

def ensure_user_exists(user_id: int, username: str):
    """Создает или обновляет пользователя"""
    cursor.execute('''
        INSERT INTO users (user_id, username) 
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET username = ?
    ''', (user_id, username, username))
    conn.commit()

def ensure_chat_exists(chat_id: int):
    """Создает чат если не существует"""
    cursor.execute('''
        INSERT OR IGNORE INTO chats (chat_id) 
        VALUES (?)
    ''', (chat_id,))
    conn.commit()

def add_game_record(user_id: int, username: str, chat_id: int, game_id: str, points: int):
    """Добавляет запись об игре"""
    ensure_user_exists(user_id, username)
    ensure_chat_exists(chat_id)
    
    cursor.execute('''
        INSERT INTO game_history (user_id, chat_id, game_id, points)
        VALUES (?, ?, ?, ?)
    ''', (user_id, chat_id, game_id, points))
    conn.commit()

def get_stats(period: str, chat_id: int):
    """Получает статистику за период"""
    time_filters = {
        'hour': "AND played_at >= datetime('now', '-1 hour')",
        'day': "AND played_at >= datetime('now', '-1 day')",
        'week': "AND played_at >= datetime('now', '-7 days')",
        'month': "AND played_at >= datetime('now', '-30 days')",
        'all': ""
    }
    
    time_filter = time_filters.get(period, "")
    
    query = f'''
        SELECT 
            u.username,
            u.tokens as total_points
        FROM users u
        WHERE EXISTS (
            SELECT 1 FROM game_history h 
            WHERE h.user_id = u.user_id 
            AND h.chat_id = ?
            {time_filter}
        )
        AND u.tokens > 0
        ORDER BY u.tokens DESC
    '''
    
    cursor.execute(query, (chat_id,))
    return cursor.fetchall()

def update_player(user_id: int, username: str, points: int, chat_id: int, game_id: str = None):
    """Обновляет статистику игрока"""
    if points > 0:  # Записываем только выигрыши
        add_game_record(user_id, username, chat_id, game_id, points)
        update_user_tokens(user_id, points)  # Добавляем выигрыш к токенам

def get_user_tokens(user_id: int) -> int:
    """Получает количество токенов пользователя"""
    cursor.execute('SELECT tokens FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def update_user_tokens(user_id: int, amount: int):
    """Обновляет количество токенов пользователя"""
    cursor.execute('UPDATE users SET tokens = tokens + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()