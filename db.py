import sqlite3

DB_LOCATION = 'clients.db'


class ClientDatabase():
    """sqlite3 database class that holds testers jobs"""

    def __init__(self, db_location) -> None:
        """Initialize db class variables"""
        self.connection = sqlite3.connect(db_location)
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

    def get_user_by_username(self, username: str) -> tuple | None:
        self.execute(f"""SELECT * FROM users
                       WHERE username = '{username}'""")
        return self.fetchone()

    def get_client_id_by_user_id(self, user_id: int) -> int | None:
        self.execute(
            f"""SELECT id from clients WHERE user_id = {user_id}""")
        return self.db.fetchone()

    def update_client_data(self, client_id: int, client_data: str) -> None:
        self.execute(f"UPDATE clients SET {client_data} "
                     f"WHERE id = '{client_id}'")
        self.commit()

    def get_disk_by_id(self, disk_id) -> tuple:
        self.execute(f"""SELECT * from disks WHERE id = {disk_id}""")
        return self.fetchone()

    def update_disk_capacity_by_id(self, disk_id: int, capacity: int) -> None:
        self.execute(f"""UPDATE disks
                        SET capacity = '{capacity}'
                        WHERE id = {disk_id}""")
        self.commit()

    def update_disk_data_by_client_id(
            self, client_id: int, disk_data: str) -> None:
        self.execute(f"UPDATE disks SET {disk_data} "
                     f"WHERE client_id = '{client_id}'")
        self.commit()

    def get_client_by_id(self, client_id: int) -> tuple:
        self.execute(f"""SELECT * from clients WHERE id = {client_id}""")
        return self.fetchone()

    def create_user(self, username: str, password: str) -> None:
        self.execute(f"""INSERT INTO users (username, password)
                               VALUES ('{username}', '{password}')""")

    def create_client(
            self, ram: int, cpu: int, hdd_capacity: int, user_id: int) -> None:
        self.execute(f"""INSERT INTO clients (ram, cpu, user_id)
                                VALUES ({ram}, {cpu}, {user_id})""")
        client_id = self.lastrowid()
        self.execute(f"""INSERT INTO disks (capacity, client_id)
                            VALUES ({hdd_capacity}, {client_id})""")

    def get_user_id_by_client_id(self, client_id: int) -> tuple:
        self.execute(
                    f"""SELECT user_id from clients WHERE id = {client_id}""")
        return self.fetchone()

    def delete_client(self, client_id: int, user_id: int) -> None:
        self.execute(f"DELETE from clients WHERE id = '{client_id}'")
        self.execute(f"DELETE from disks WHERE client_id = '{client_id}'")
        self.execute(f"DELETE from users WHERE id = '{user_id}'")
        self.commit()

    def get_clients(self) -> tuple:
        self.execute("""SELECT users.id, users.username,
                     clients.ram, clients.cpu, disks.id,
                     disks.capacity
                     FROM clients
                     JOIN disks on clients.id = disks.client_id
                     JOIN users ON clients.user_id = users.id""")
        return self.fetchall()

    def get_clients_by_ids(self, clients_ids: str) -> tuple:
        self.execute(f"""SELECT users.id, users.username,
                     clients.ram, clients.cpu, disks.id,
                     disks.capacity
                     FROM clients
                     JOIN disks on clients.id = disks.client_id
                     JOIN users ON clients.user_id = users.id
                     WHERE users.id
                     IN ({clients_ids})""")
        return self.fetchall()

    def get_statistic(self) -> tuple:
        self.execute("""SELECT COUNT(*), SUM(ram), SUM(cpu)
                     FROM clients""")
        return self.fetchone()

    def get_disks(self) -> tuple:
        self.execute("""SELECT disks.id, disks.capacity,
                     disks.client_id, clients.ram, clients.cpu,
                     clients.user_id
                     FROM disks
                     JOIN clients ON disks.client_id = clients.id""")
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


db = ClientDatabase(DB_LOCATION)
db.create_tables()
