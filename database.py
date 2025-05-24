import sqlite3
from contextlib import closing

def init_db():
    with closing(sqlite3.connect('user_data.db')) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
        ''')
        conn.commit()

def update_balance(user_id: int, amount: int):
    with closing(sqlite3.connect('user_data.db')) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, balance)
        VALUES (?, ?)
        ''', (user_id, amount))
        conn.commit()

def get_balance(user_id: int) -> int:
    with closing(sqlite3.connect('user_data.db')) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0