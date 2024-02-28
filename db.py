import sqlite3


class DatabaseManager:
    def __init__(self, db_filename):
        self.db_filename = db_filename
        self.create_table()

    def create_table(self):
        with sqlite3.connect(self.db_filename) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT
                )
            ''')
            conn.commit()

    def add_user(self, telegram_id, username=None, first_name=None, last_name=None, ):
        try:
            with sqlite3.connect(self.db_filename) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, username, first_name, last_name))
                conn.commit()
            return True
        except sqlite3.IntegrityError:  # User already exists
            return False

    def user_exists(self, telegram_id):
        with sqlite3.connect(self.db_filename) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            result = cursor.fetchone()
            return result is not None


# Пример использования:
if __name__ == '__main__':
    db_manager = DatabaseManager('example.db')
    telegram_id = 123456780  # Пример идентификатора пользователя Telegram

    # Проверяем, существует ли пользователь
    if not db_manager.user_exists(telegram_id):
        # Добавляем пользователя, если он не существует
        if db_manager.add_user(telegram_id):
            print("Пользователь успешно добавлен.")
        else:
            print("Не удалось добавить пользователя.")
    else:
        print("Пользователь уже существует в базе данных.")
