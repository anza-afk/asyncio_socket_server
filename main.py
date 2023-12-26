import asyncio
import sqlite3

from db import conn, cursor


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.authenticated_users = {}

    async def register(self, reader, writer):
        # Получаем данные от клиента
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
            conn.commit()
            writer.write('Succsessful registration!'.encode())
            user_id = cursor.lastrowid
            await self.add_client(reader, writer, user_id)
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Database data corrupted, {e}".encode())

    async def authenticate(self, reader, writer, addr):
        # Получаем данные от клиента
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
                # Если клиент найден, проверяем, правильный ли пароль ввел
                # пользователь
                if password == user[2]:
                    # Если пароль верный, обновляем статус клиента
                    # в базе данных на авторизованный
                    writer.write("Successful authentication".encode())
                    self.authenticated_users[username] = {
                        'ip': addr[0], 'port': addr[1]}
                    await self.update_client(reader, writer, user[0])
                    # Отправляем клиенту подтверждение
                    await writer.drain()
                else:
                    # Если пароль неверный, отправляем клиенту
                    # сообщение об ошибке
                    writer.write(
                        "Authentication failed: wrong password".encode())
                    await writer.drain()
            else:
                # Если клиент не найден, отправляем клиенту сообщение об ошибке
                writer.write("Authentication failed: user not found".encode())
                await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Database data corrupted, {e}".encode())

    async def add_client(self, reader, writer, user_id):
        # Получаем данные от клиента
        data = await reader.read(1024)
        message = data.decode()
        # Разбиваем данные на параметры
        params = message.replace(' ', '').split(',')
        # Добавляем клиента в базу данных
        try:
            cursor.execute("""INSERT INTO clients (ram, cpu, hdd_capacity,
                           user_id) VALUES (?, ?, ?, ?)""",
                           (params[0], params[1], params[2], user_id))
            conn.commit()
            # Отправляем клиенту подтверждение
            writer.write("Client added to database".encode())
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Client data corrupted, {e}".encode())
            await writer.drain()

    async def update_client(self, reader, writer, user_id):
        # Получаем данные от клиента
        data = await reader.read(1024)
        message = data.decode()
        # Разбиваем данные на параметры
        params = message.replace(' ', '').split(',')
        # Обновляем данные авторизованного клиента в базе данных
        try:
            cursor.execute("""UPDATE clients SET ram = ?, cpu = ?,
                           hdd_capacity = ? WHERE id = ?""",
                           (params[0], params[1], params[2], user_id))
            conn.commit()
            writer.write("Client data updated".encode())
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Client data corrupted, {e}".encode())
            await writer.drain()
        # Отправляем клиенту подтверждение

    async def get_all_clients(self, reader, writer):
        # Получаем список всех клиентов из базы данных
        cursor.execute("""SELECT * FROM clients JOIN disks
                    ON clients.id=disks.client_id""")
        clients = cursor.fetchall()

        # Отправляем список клиентов клиенту
        for client in clients:
            writer.write(str(client).encode())
            await writer.drain()

    async def get_authorized_clients(self, reader, writer):
        # Получаем список всех авторизованных клиентов
        try:
            usernames = ", ".join(
                f"'{s}'" for s in self.authenticated_users.keys())
            cursor.execute(f"""SELECT clients.ram, clients.cpu,
                           clients.hdd_capacity FROM clients JOIN users
                           ON clients.user_id = users.id
                           WHERE users.username
                           IN ({usernames})""")
            db_clients = cursor.fetchall()
            print(db_clients)
            # Отправляем список клиентов клиенту
            clients = ', '.join([
                f'ram: {client[0]} cpu: {client[1]} hdd: {client[2]}'
                for client in db_clients])
            writer.write(clients.encode())
            await writer.drain()
        except sqlite3.OperationalError as e:
            writer.write(f"Client data corrupted, {e}".encode())
            await writer.drain()

    async def get_all_connected_clients(self, reader, writer):
        # Получаем список всех когда-либо подключаемых клиентов из базы данных
        cursor.execute("SELECT * FROM clients")
        clients = cursor.fetchall()

        # Отправляем список клиентов клиенту
        for client in clients:
            writer.write(str(client).encode())
            await writer.drain()

    async def add_disk(self, reader, writer):
        # Получаем данные от клиента
        writer.write('input your disk data:'.encode())
        data = await reader.read(1024)
        message = data.decode()

        # Разбиваем данные на параметры
        params = message.split(',')

        # Добавляем жесткий диск клиента в базу данных
        cursor.execute("INSERT INTO disks (client_id, hdd_id) VALUES (?, ?)",
                       (params[0], params[1]))
        conn.commit()

        # Отправляем клиенту подтверждение
        writer.write("Disk added to client".encode())
        await writer.drain()

    async def get_all_disks(self, reader, writer):
        # Получаем список всех жестких дисков из базы данных
        cursor.execute("SELECT * FROM disks")
        disks = cursor.fetchall()

        # Отправляем список жестких дисков клиенту
        for disk in disks:
            writer.write(str(disk).encode())
            await writer.drain()

    async def quit(self, reader, writer):
        # Закрываем соединение с клиентом
        writer.close()
        await writer.wait_closed()

    async def handle_connection(self, reader, writer):
        addr = writer.get_extra_info("peername")
        print("Connected by", addr)
        while True:
            # Receive
            try:
                data = await reader.read(1024)
            except ConnectionError:
                print(f"Client suddenly closed while receiving from {addr}")
                break
            if not data:
                break
            message = data.decode()
            try:
                match message:
                    case 'register':
                        await self.register(reader, writer)
                    # case "add_client":
                    #     await self.add_client(reader, writer)
                    case "get_all_clients":
                        await self.get_all_clients(reader, writer)
                    case "get_authorized_clients":
                        await self.get_authorized_clients(reader, writer)
                    case "get_all_connected_clients":
                        await self.get_all_connected_clients(reader, writer)
                    # case "update_client":
                    #     await self.update_client(reader, writer)
                    case "add_disk":
                        await self.add_disk(reader, writer)
                    case "get_all_disks":
                        await self.get_all_disks(reader, writer)
                    case "authenticate":
                        await self.authenticate(reader, writer, addr)
                    case "quit":
                        await quit(reader, writer)
                    case _:
                        writer.write('Unrecognised command!'.encode())
            except ConnectionError:
                print("Client suddenly closed, cannot send")
                break
        writer.close()
        print("Disconnected by", addr)

    async def main(self):
        server = await asyncio.start_server(
            self.handle_connection, self.host, self.port)
        async with server:
            await server.serve_forever()


HOST, PORT = "", 50007


if __name__ == "__main__":
    server = Server(HOST, PORT)
    asyncio.run(server.main())
