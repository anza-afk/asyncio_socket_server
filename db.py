import sqlite3

# Создаем базу данных
conn = sqlite3.connect('clients.db')
cursor = conn.cursor()

# Создаём таблицу users
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY, username TEXT,
                  password TEXT)''')

# Создаем таблицу clients
cursor.execute('''CREATE TABLE IF NOT EXISTS clients
                  (id INTEGER PRIMARY KEY, ram INTEGER,
                  cpu INTEGER, user_id INTEGER,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')

# Создаем таблицу disks
cursor.execute('''CREATE TABLE IF NOT EXISTS disks
                  (id INTEGER PRIMARY KEY, capacity INT, client_id INT,
                  FOREIGN KEY(client_id) REFERENCES client(id))''')
