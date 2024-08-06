import sqlite3

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            chosen_person TEXT
        )
    ''')
    conn.commit()
    conn.close()

def set_user_person(user_id, person):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('REPLACE INTO users (user_id, chosen_person) VALUES (?, ?)', (user_id, person))
    conn.commit()
    conn.close()

def get_user_person(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT chosen_person FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None
