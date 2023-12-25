import sqlite3

# Создаем базу данных
conn = sqlite3.connect('clients.db')
cursor = conn.cursor()

# Создаём таблицу users
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY, username STRING,
                  password STRING)''')

# Создаем таблицу clients
cursor.execute('''CREATE TABLE IF NOT EXISTS clients
                  (id INTEGER PRIMARY KEY, ram INTEGER,
                  cpu INTEGER, hdd_capacity INTEGER)''')

# # Создаем таблицу disks
# cursor.execute('''CREATE TABLE IF NOT EXISTS disks
#                   (id INTEGER PRIMARY KEY, client_id INTEGER,
#                   )''')
