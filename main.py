import asyncio
from asyncio import StreamReader, StreamWriter

import sqlite3

from db import db


class Server:
    def __init__(self, host, port, conn, cursor):
        self.host = host
        self.port = port
        self.db = db
        self.connected_clients = {}

    async def register(
            self, reader: StreamReader, writer: StreamWriter) -> None:
        """
        Метод регистрации на сервере.
        Содаёт объект user с username и password
        Вызывает метод создания клиента с базовым параметрами.
        """
        writer.write('input your username:'.encode())
        data = await reader.read(1024)
        username = data.decode()
        if self.db.check_username_exists(username):
            writer.write('Client with this username '
                         'already registered'.encode())
            await writer.drain()
        else:
            writer.write('input your password:'.encode())
            data = await reader.read(1024)
            password = data.decode()
            try:
                self.db.execute(f"""INSERT INTO users (username, password)
                               VALUES ('{username}', '{password}')""")
                user_id = self.db.lastrowid
                await self._add_client(
                    writer, ram=2048, cpu=2, hdd_capacity=2048,
                    user_id=user_id)
                # Отправляем клиенту подтверждение
                writer.write('Succsessful registration!'.encode())
                await writer.drain()
            except sqlite3.OperationalError as e:
                writer.write(f"Database data corrupted, {e}".encode())

    async def _add_client(
            self, writer: StreamWriter,
            ram: int,
            cpu: int,
            hdd_capacity: int,
            user_id: int
    ) -> None:
        """Метод записи клиента в базу данных"""
        try:
            self.db.execute(f"""INSERT INTO clients (ram, cpu, user_id)
                                VALUES ({ram}, {cpu}, {user_id})""")
            client_id = self.db.lastrowid
            self.db.execute(f"""INSERT INTO disks (capacity, client_id)
                                VALUES ({hdd_capacity}, {client_id})""")
            self.db.commit()
            print("Client added to database")
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Database error: {e}".encode())
            await writer.drain()

    async def login(
            self,
            reader: StreamReader,
            writer: StreamWriter,
            addr: tuple(str, int)
    ) -> None:
        """Метод аутентификации клиента."""
        writer.write('input your username:'.encode())
        data = await reader.read(1024)
        username = data.decode()
        writer.write('input your password:'.encode())
        data = await reader.read(1024)
        password = data.decode()

        # Проверяем, есть ли клиент с таким username в базе данных
        try:
            self.db.execute(f"""SELECT * FROM users
                                WHERE username = '{username}'""")
            user = self.db.fetchone()
            if user:
                # Если клиент найден, проверяем пароль и добавляем
                # клиента в список авторизованных
                if password == user[2]:
                    writer.write("Successful authentication\nAvaible commands:"
                                 "\nget_all_clients, get_authorized_clients, "
                                 "get_all_connected_clients, get_all_disks, "
                                 "delete_client, get_statistic, "
                                 "update_params, quit".encode())
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
            self,
            reader: StreamReader,
            writer: StreamWriter,
            addr: tuple(str, int)
    ) -> None:
        """Метод обновления авторизованного клиента в базе данных"""
        # Получаем ID авторизованного клиента
        user_id = self.connected_clients.get(addr)['id']
        self.db.execute(
            f"""SELECT id from clients WHERE user_id = {user_id}""")
        client_id = self.db.fetchone()
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
                self.db.execute(f"UPDATE clients SET {clients_data} "
                                f"WHERE id = '{client_id}'")
            if disk_data:
                self.db.execute(f"UPDATE disks SET {disk_data} "
                                f"WHERE client_id = '{client_id}'")
            self.db.commit()
            # Отправляем клиенту подтверждение
            writer.write("Client data updated".encode())
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Database error: {e}".encode())
            await writer.drain()

    async def update_clients_and_disks(
            self, reader: StreamReader, writer: StreamWriter) -> None:
        """Метод обновления параметры клиента или диска в базе данных по ID"""
        writer.write('Enter what do you want to update.\n'
                     'Avaible choices: client, disk'.encode())
        data = await reader.read(1024)
        message = data.decode().strip()
        try:
            match message.lower():
                case 'disk':
                    writer.write('Enter ID of disk to update.'.encode())
                    data = await reader.read(1024)
                    disk_id = data.decode()
                    self.db.execute(
                        f"""SELECT * from disks WHERE id = {disk_id}""")
                    if self.db.fetchone():
                        writer.write('Enter new capacity of disk'
                                     f' {disk_id}'.encode())
                        data = await reader.read(1024)
                        capacity = data.decode()
                        self.db.execute(f"""UPDATE disks
                                                SET capacity = '{capacity}'
                                                WHERE id = {disk_id}""")
                        self.db.commit()
                        writer.write("Disk data updated".encode())
                    else:
                        writer.write(f"Disk with id {disk_id}"
                                     " not found".encode())
                        await writer.drain()
                case 'client':
                    writer.write('Enter ID of client to update.'.encode())
                    data = await reader.read(1024)
                    client_id = data.decode()
                    self.db.execute(
                        f"""SELECT * from clients WHERE id = {client_id}""")
                    if self.db.fetchone():
                        writer.write('What parameters to update?\n'
                                     'format: param=value, param=value'
                                     '\nAccepted params: ram, cpu'.encode())
                        data = await reader.read(1024)
                        params = data.decode().replace(
                            ' ', '').split(',')
                        clients_data = ', '.join(param for param in params
                                                 if 'ram' in param
                                                 or 'cpu' in param)
                        self.db.execute("UPDATE clients "
                                        f"SET {clients_data} "
                                        f"WHERE id = '{client_id}'")
                        self.db.commit()
                        # Отправляем клиенту подтверждение
                        writer.write("Client data updated".encode())
                    else:
                        writer.write(f"Client with id {client_id}"
                                     " not found".encode())
                        await writer.drain()
                case _:
                    writer.write('Unrecognised command'.encode())
                    await writer.drain()
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Database error: {e}".encode())
            await writer.drain()

    async def delete_client(
            self,
            reader: StreamReader,
            writer: StreamWriter,
            addr: tuple(str, int)
    ) -> None:
        """Метод удаления клиента по ID"""
        writer.write(
            "Enter the ID of the client that needs to be deleted or 'cancel'"
            " for cancel operation".encode())
        data = await reader.read(1024)
        message = data.decode()
        if message.lower() == "cancel":
            writer.write("Operation canceled.".encode())
            await writer.drain()
        else:
            try:
                client_id = int(message)
                self.db.execute(
                    f"""SELECT user_id from clients WHERE id = {client_id}""")
                if user := self.db.fetchone():
                    current_user_id = self.connected_clients.get(addr)['id']
                    if current_user_id != user[0]:
                        self.db.execute("DELETE from clients "
                                        f"WHERE id = '{client_id}'")
                        self.db.execute("DELETE from disks "
                                        "WHERE client_id = "
                                        f"'{client_id}'")
                        self.db.execute(f"DELETE from users "
                                        f"WHERE id = '{user[0]}'")
                        self.db.commit()
                        writer.write(f"Client with id {client_id}"
                                     " deleted".encode())
                        await writer.drain()
                    else:
                        writer.write("Can't delete yourself".encode())
                        await writer.drain()
                else:
                    writer.write(f"Client with id {client_id}"
                                 " not found".encode())
                    await writer.drain()

            except ValueError:
                writer.write("ID must be integer!".encode())
                await writer.drain()
            except sqlite3.OperationalError as e:
                writer.write(f"Database error: {e}".encode())
                await writer.drain()

    async def get_all_clients(self, writer: StreamWriter) -> None:
        """Метод получения всех подключенных клиентов из базы данных"""
        self.db.execute("""SELECT users.id, users.username,
                                clients.ram, clients.cpu, disks.id,
                                disks.capacity
                                FROM clients
                                JOIN disks on clients.id = disks.client_id
                                JOIN users ON clients.user_id = users.id""")
        db_clients = self.db.fetchall()
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

    async def get_connected_clients(
            self, writer: StreamWriter, authorized=False) -> None:
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
            self.db.execute(f"""SELECT users.id, users.username,
                                clients.ram, clients.cpu, disks.id,
                                disks.capacity
                                FROM clients
                                JOIN disks on clients.id = disks.client_id
                                JOIN users ON clients.user_id = users.id
                                WHERE users.id
                                IN ({clients_ids})""")
            db_clients = self.db.fetchall()
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
            # Отправляем клиенту список клиентов
            writer.write(str(clients).encode())
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Database error: {e}".encode())
            await writer.drain()

    async def get_all_disks(self, writer: StreamWriter) -> None:
        """Метод получения всех жёстких дисков с параметрами клиентов"""
        self.db.execute("""SELECT disks.id, disks.capacity,
                            disks.client_id, clients.ram, clients.cpu,
                            clients.user_id
                            FROM disks
                            JOIN clients ON disks.client_id = clients.id""")
        db_disks = self.db.fetchall()
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

    async def get_statistic(self, writer: StreamWriter) -> None:
        """
        Метод получения общего количество машин,
        общий объем RAM и CPU, используемый всеми машинами.
        """
        self.db.execute("""SELECT COUNT(*), SUM(ram), SUM(cpu)
                            FROM clients""")
        statistic = self.db.fetchone()
        statistic = {
            'client_count': statistic[0],
            'total_ram': statistic[1],
            'total_cpu': statistic[2]
        }
        # Отправляем статистику клиенту
        writer.write(str(statistic).encode())
        await writer.drain()

    async def quit(self, writer: StreamWriter, addr: str) -> None:
        """Метод выхода клиента с сервера."""
        writer.close()
        self.connected_clients.pop(addr)
        await writer.wait_closed()

    async def handle_connection(
            self, reader: StreamReader, writer: StreamWriter) -> None:
        """Метод обработки подключений сервера."""
        addr = writer.get_extra_info("peername")
        print("Connected by", addr)
        # Добавляем неавторизованного клиента
        self.connected_clients[addr] = {'authorized': False}
        writer.write("Hello! For sing in type login\n"
                     "For sing up type register".encode())
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
                        # Методы, доступные неавторизованному клиенту
                        case 'register':
                            await self.register(reader, writer)
                        case "login":
                            await self.login(reader, writer, addr)
                        case "quit":
                            await quit(writer)
                        case ("get_all_clients" | "get_authorized_clients" |
                              "get_all_connected_clients" | "get_all_disks" |
                              "delete_client" | "get_statistic" |
                              "update_params"):
                            writer.write(
                                'Please authentificate with "login"'
                                ' first.'.encode()
                            )
                        case _:
                            writer.write('Unrecognised command!'.encode())
                else:
                    match message.lower():
                        # Методы, доступные авторизованному клиенту
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
                        case "update_params":
                            await self.update_clients_and_disks(
                                reader, writer)
                        case "get_all_disks":
                            await self.get_all_disks(writer)
                        case "delete_client":
                            await self.delete_client(reader, writer, addr)
                        case "get_statistic":
                            await self.get_statistic(writer)
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

    async def main(self) -> None:
        server = await asyncio.start_server(
            self.handle_connection, self.host, self.port)
        async with server:
            await server.serve_forever()


HOST, PORT = "", 50007


if __name__ == "__main__":
    server = Server(HOST, PORT, db)
    asyncio.run(server.main())
