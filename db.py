import sqlite3

# Создаем базу данных
conn = sqlite3.connect('clients.db')
cursor = conn.cursor()

# Создаём таблицу users
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                  password TEXT NOT NULL)''')

# Создаем таблицу clients
cursor.execute('''CREATE TABLE IF NOT EXISTS clients
                  (id INTEGER PRIMARY KEY, ram INTEGER,
                  cpu INTEGER, user_id INTEGER,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')

# Создаем таблицу disks
cursor.execute('''CREATE TABLE IF NOT EXISTS disks
                  (id INTEGER PRIMARY KEY, capacity INT, client_id INT UNIQUE,
                  FOREIGN KEY(client_id) REFERENCES client(id))''')


class ClientDatabase(object):
    """sqlite3 database class that holds testers jobs"""
    DB_LOCATION = 'clients.db'

    def __init__(self) -> None:
        """Initialize db class variables"""
        self.connection = sqlite3.connect(ClientDatabase.DB_LOCATION)
        self.cur = self.connection.cursor()

    def close(self) -> None:
        """close sqlite3 connection"""
        self.connection.close()

    def lastrowid(self) -> int:
        return self.cur.lastrowid

    def fetchone(self) -> int:
        return self.cur.fetchone()

    def fetchall(self) -> int:
        return self.cur.fetchall()

    def execute(self, new_data) -> None:
        """execute a row of data to current cursor"""
        self.cur.execute(new_data)

    def check_username(self, username: str) -> bool:
        self.execute(f"""SELECT * FROM users
                       WHERE username = '{username}'""")
        return self.fetchall()

    def create_tables(self) -> None:
        """create a database tables if it does not exist already"""
        self.cur.execute('''CREATE TABLE IF NOT EXISTS users
                        (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL)''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS clients
                        (id INTEGER PRIMARY KEY, ram INTEGER,
                        cpu INTEGER, user_id INTEGER,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS disks
                        (id INTEGER PRIMARY KEY, capacity INT,
                         client_id INT UNIQUE, FOREIGN KEY(client_id)
                         REFERENCES client(id))''')

    def commit(self) -> None:
        """commit changes to database"""
        self.connection.commit()


db = ClientDatabase
db.create_tables()
