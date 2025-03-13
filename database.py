import sqlite3
from datetime import datetime

# Подключение к базе данных
conn = sqlite3.connect('stats.sqlite', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы players
def init_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER,
            chat_id INTEGER,
            username TEXT,
            total_points INTEGER DEFAULT 0,
            month_points INTEGER DEFAULT 0,
            week_points INTEGER DEFAULT 0,
            day_points INTEGER DEFAULT 0,
            last_updated DATE,
            PRIMARY KEY (user_id, chat_id)  
        )
    ''')
    conn.commit()

# Получение данных игрока
def get_player(user_id, chat_id):
    cursor.execute('SELECT * FROM players WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    return cursor.fetchone()

# Добавление или обновление данных игрока
def update_player(user_id, username, points, chat_id):
    today = datetime.now().date()
    player = get_player(user_id, chat_id)

    if player:
        # Обновляем данные игрока
        cursor.execute('''
            UPDATE players
            SET 
                total_points = total_points + ?,
                month_points = month_points + ?,
                week_points = week_points + ?,
                day_points = day_points + ?,
                last_updated = ?
            WHERE user_id = ? AND chat_id = ?
        ''', (points, points, points, points, today, user_id, chat_id))
    else:
        # Добавляем нового игрока
        cursor.execute('''
            INSERT INTO players (user_id, chat_id, username, total_points, month_points, week_points, day_points, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, chat_id, username, points, points, points, points, today))
    
    conn.commit()

# Сброс статистики за день/неделю/месяц
def reset_stats(period, chat_id):
    today = datetime.now().date()
    if period == 'day':
        cursor.execute('UPDATE players SET day_points = 0, last_updated = ? WHERE chat_id = ?', (today, chat_id))
    elif period == 'week':
        cursor.execute('UPDATE players SET week_points = 0, last_updated = ? WHERE chat_id = ?', (today, chat_id))
    elif period == 'month':
        cursor.execute('UPDATE players SET month_points = 0, last_updated = ? WHERE chat_id = ?', (today, chat_id))
    conn.commit()

# Получение статистики
def get_stats(period, chat_id):
    if period == 'all':
        cursor.execute('SELECT username, total_points FROM players WHERE chat_id = ? ORDER BY total_points DESC', (chat_id,))
    elif period == 'month':
        cursor.execute('SELECT username, month_points FROM players WHERE chat_id = ? ORDER BY month_points DESC', (chat_id,))
    elif period == 'week':
        cursor.execute('SELECT username, week_points FROM players WHERE chat_id = ? ORDER BY week_points DESC', (chat_id,))
    elif period == 'day':
        cursor.execute('SELECT username, day_points FROM players WHERE chat_id = ? ORDER BY day_points DESC', (chat_id,))
    return cursor.fetchall()