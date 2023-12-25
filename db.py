import sqlite3

# Создаем базу данных
conn = sqlite3.connect('clients.db')
cursor = conn.cursor()

# Создаем таблицу clients
cursor.execute('''CREATE TABLE IF NOT EXISTS clients
                  (id INTEGER PRIMARY KEY, ram INTEGER,
                  cpu INTEGER)''')

# Создаем таблицу disks
cursor.execute('''CREATE TABLE IF NOT EXISTS disks
                  (id INTEGER PRIMARY KEY, client_id INTEGER,
                  hdd_capacity INTEGER)''')
