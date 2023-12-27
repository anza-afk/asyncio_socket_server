import asyncio
import sqlite3

from db import conn, cursor


class Server:
    def __init__(self, host, port, conn, cursor):
        self.host = host
        self.port = port
        self.connection = conn
        self.cursor = cursor
        self.connected_clients = {}

    async def register(self, reader, writer):
        """
        Метод регистрации на сервере.
        Содаёт объект user с username и password
        Вызывает метод создания клиента с базовым параметрами.
        """
        writer.write('input your username:'.encode())
        data = await reader.read(1024)
        username = data.decode()
        writer.write('input your password:'.encode())
        data = await reader.read(1024)
        password = data.decode()
        try:
            cursor.execute("""INSERT INTO users (username, password)
                           VALUES (?, ?)""",
                           (username, password))

            user_id = cursor.lastrowid
            await self._add_client(
                reader, writer, ram=2048, cpu=2, hdd_capacity=2048,
                user_id=user_id)

            writer.write('Succsessful registration!'.encode())
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Database data corrupted, {e}".encode())

    async def _add_client(self, writer, ram, cpu, hdd_capacity, user_id):
        """Метод записи клиента в базу данных"""
        try:
            self.cursor.execute("""INSERT INTO clients (ram, cpu, user_id)
                                VALUES (?, ?, ?)""",
                                (ram, cpu, user_id))
            client_id = self.cursor.lastrowid
            self.cursor.execute("""INSERT INTO disks (capacity, client_id)
                                VALUES (?, ?)""",
                                (hdd_capacity, client_id))
            self.connection.commit()
            # Отправляем клиенту подтверждение
            print("Client added to database")
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Client data corrupted, {e}".encode())
            await writer.drain()

    async def login(self, reader, writer, addr):
        """Метод аутентификации клиента."""
        writer.write('input your username:'.encode())
        data = await reader.read(1024)
        username = data.decode()
        writer.write('input your password:'.encode())
        data = await reader.read(1024)
        password = data.decode()

        # Проверяем, есть ли клиент с таким username в базе данных
        try:
            cursor.execute("SELECT * FROM users WHERE username = ?",
                           (username,))
            user = cursor.fetchone()
            if user:
                # Если клиент найден, проверяем пароль и добавляем
                # клиента в список авторизованных
                if password == user[2]:
                    writer.write("Successful authentication".encode())
                    self.connected_clients[addr]['authorized'] = True
                    self.connected_clients[addr]['id'] = user[0]
                    await writer.drain()
                else:
                    # Если пароль неверный, отправляем сообщение об ошибке
                    writer.write(
                        "Authentication failed: wrong password".encode())
                    await writer.drain()
            else:
                # Если клиент не найден, отправляем клиенту сообщение об ошибке
                writer.write("Authentication failed: user not found".encode())
                await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Database data corrupted, {e}".encode())

    async def update_client(
            self, reader, writer, addr):
        # Обновляем данные авторизованного клиента в базе данных
        user_id = self.connected_clients.get(addr)['id']
        self.cursor.execute(
            f"""SELECT id from clients WHERE user_id = {user_id}""")
        client_id = cursor.fetchone()[0]

        writer.write('What parameters to update?\nformat: param=value, '
                     'param=value\nAccepted params: ram, cpu, '
                     'capacity'.encode())
        data = await reader.read(1024)
        params = data.decode().replace(' ', '').split(',')
        clients_data = ', '.join(param for param in params
                                 if 'ram' in param or 'cpu' in param)
        disk_data = ', '.join(param for param in params if 'capacity' in param)
        try:
            if clients_data:
                self.connection.execute(f"UPDATE clients SET {clients_data} "
                                        "WHERE id = '{client_id}'")
            if disk_data:
                self.connection.execute(f"UPDATE disks SET {disk_data}"
                                        f"WHERE id = '{client_id}'")
            self.connection.commit()
            writer.write("Client data updated".encode())
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Client data corrupted, {e}".encode())
            await writer.drain()
        # Отправляем клиенту подтверждение

    async def get_all_clients(self, writer):
        """Метод получения всех подключенных клиентов из базы данных"""
        self.cursor.execute("""SELECT users.id, users.username,
                                clients.ram, clients.cpu, disks.id,
                                disks.capacity
                                FROM clients
                                JOIN disks on clients.id = disks.client_id
                                JOIN users ON clients.user_id = users.id""")
        db_clients = self.cursor.fetchall()
        clients = [{
                    'user_id': db_client[0],
                    'username': db_client[1],
                    'ram': db_client[2],
                    'cpu': db_client[3],
                    'hdd_id': db_client[4],
                    'hdd_capacity': db_client[5]
                } for db_client in db_clients]
        # Отправляем список клиентов клиенту
        writer.write(str(clients).encode())
        await writer.drain()

    async def get_connected_clients(self, writer, authorized=False):
        """Метод получения всех подключенных клиентов
        с параметром authorized возвращает только авторизованных."""
        try:
            # Получаем список всех авторизованных клиентов
            if authorized:
                suitable_clients = {key: value for key, value
                                    in self.connected_clients.items()
                                    if value['authorized']}
            # Получаем список всех клиентов
            else:
                suitable_clients = self.connected_clients

            clients_ids = ", ".join(f"'{data['id']}'"
                                    for data in suitable_clients.values()
                                    if data.get('id'))
            self.cursor.execute(f"""SELECT users.id, users.username,
                                clients.ram, clients.cpu, disks.id,
                                disks.capacity
                                FROM clients
                                JOIN disks on clients.id = disks.client_id
                                JOIN users ON clients.user_id = users.id
                                WHERE users.id
                                IN ({clients_ids})""")
            db_clients = self.cursor.fetchall()
            clients = []
            for socket, data in suitable_clients.items():
                if connected_id := data.get('id'):
                    for db_client in db_clients:
                        if connected_id == db_client[0]:
                            clients.append(
                                {
                                    'socket': socket,
                                    'authorized': data['authorized'],
                                    'user_id': db_client[0],
                                    'username': db_client[1],
                                    'ram': db_client[2],
                                    'cpu': db_client[3],
                                    'hdd_id': db_client[4],
                                    'hdd_capacity': db_client[5]
                                }
                            )
                            break
                else:
                    clients.append(
                        {
                            'socket': socket,
                            'authorized': data['authorized'],
                        }
                    )
            writer.write(str(clients).encode())
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Client data corrupted, {e}".encode())
            await writer.drain()

    async def get_all_disks(self, writer):
        """Метод получения всех жёстких дисков с параметрами клиентов"""
        self.cursor.execute("""SELECT disks.id, disks.capacity,
                            disks.client_id, clients.ram, clients.cpu,
                            clients.user_id
                            FROM disks
                            JOIN clients ON disks.client_id = clients.id""")
        db_disks = self.cursor.fetchall()
        disks = [{
                'disk_id': db_disk[0],
                'disk_capacity': db_disk[1],
                'client_id': db_disk[2],
                'ram': db_disk[3],
                'cpu': db_disk[4],
                'user_id': db_disk[5]
                } for db_disk in db_disks]
        # Отправляем список жестких дисков клиенту
        writer.write(str(disks).encode())
        await writer.drain()

    async def quit(self, writer, addr):
        """Метод выхода клиента с сервера."""
        writer.close()
        self.connected_clients.pop(addr)
        await writer.wait_closed()

    async def handle_connection(self, reader, writer):
        """Метод обработки подключений сервера."""
        addr = writer.get_extra_info("peername")
        print("Connected by", addr)
        # Добавляем неавторизованного клиента
        self.connected_clients[addr] = {'authorized': False}
        while True:
            try:
                data = await reader.read(1024)
            except ConnectionError:
                print(f"Client suddenly closed while receiving from {addr}")
                break
            if not data:
                break
            message = data.decode()
            try:
                if not self.connected_clients[addr]['authorized']:
                    match message:
                        # Методы, достпные неавторизованному клиенту
                        case 'register':
                            await self.register(reader, writer)
                        case "login":
                            await self.login(reader, writer, addr)
                        case "quit":
                            await quit(writer)
                        case ("get_all_clients" | "get_authorized_clients" |
                              "get_all_connected_clients" | "get_all_disks"):
                            writer.write(
                                'Please authentificate with "login"'
                                ' first.'.encode()
                            )
                        case _:
                            writer.write('Unrecognised command!'.encode())
                else:
                    match message:
                        # Методы, достпные авторизованному клиенту
                        case "get_all_clients":
                            await self.get_all_clients(writer)

                        case "get_authorized_clients":
                            await self.get_connected_clients(
                                writer, authorized=True
                            )
                        case "get_connected_clients":
                            await self.get_connected_clients(writer)
                        case "update_client":
                            await self.update_client(reader, writer, addr)
                        case "get_all_disks":
                            await self.get_all_disks(writer)
                        case "quit":
                            await quit(writer)
                        case _:
                            writer.write('Unrecognised command!'.encode())
            except ConnectionError:
                print("Client suddenly closed, cannot send")
                break
        writer.close()
        self.connected_clients.pop(addr)
        print("Disconnected by", addr)

    async def main(self):
        server = await asyncio.start_server(
            self.handle_connection, self.host, self.port)
        async with server:
            await server.serve_forever()


HOST, PORT = "", 50007


if __name__ == "__main__":
    server = Server(HOST, PORT, conn, cursor)
    asyncio.run(server.main())
