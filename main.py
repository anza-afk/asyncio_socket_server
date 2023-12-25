import asyncio

from db import conn, cursor


async def add_client(reader, writer):
    # Получаем данные от клиента
    writer.write('input your data:'.encode())
    data = await reader.read(1024)
    message = data.decode()
    # Разбиваем данные на параметры
    print(message)
    params = message.replace(' ', '').split(',')
    # Добавляем клиента в базу данных
    cursor.execute("INSERT INTO clients (ram, cpu) VALUES (?, ?)",
                   (params[0], params[1]))
    print(cursor.lastrowid)
    cursor.execute("INSERT INTO disks (client_id, hdd_capacity) VALUES (?, ?)",
                   (cursor.lastrowid, params[2]))
    conn.commit()
    print('done')
    # Отправляем клиенту подтверждение
    writer.write("Client added to database".encode())
    await writer.drain()


async def get_all_clients(reader, writer):
    # Получаем список всех клиентов из базы данных
    cursor.execute("""SELECT * FROM clients JOIN disks
                   ON clients.id=disks.client_id""")
    clients = cursor.fetchall()

    # Отправляем список клиентов клиенту
    for client in clients:
        writer.write(str(client).encode())
        await writer.drain()


async def get_authorized_clients(reader, writer):
    # Получаем список всех авторизованных клиентов из базы данных
    cursor.execute("SELECT * FROM clients WHERE authorized = 1")
    clients = cursor.fetchall()

    # Отправляем список клиентов клиенту
    for client in clients:
        writer.write(str(client).encode())
        await writer.drain()


async def get_all_connected_clients(reader, writer):
    # Получаем список всех когда-либо подключаемых клиентов из базы данных
    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()

    # Отправляем список клиентов клиенту
    for client in clients:
        writer.write(str(client).encode())
        await writer.drain()


async def update_client(reader, writer):
    # Получаем данные от клиента
    writer.write('input your update data:'.encode())
    data = await reader.read(1024)
    message = data.decode()

    # Разбиваем данные на параметры
    params = message.split(',')

    # Обновляем данные авторизованного клиента в базе данных
    cursor.execute("""UPDATE clients SET ram = ?, cpu = ?, hdd = ?
                   WHERE id = ? AND authorized = 1""",
                   (params[1], params[2], params[3], params[0]))
    conn.commit()

    # Отправляем клиенту подтверждение
    writer.write("Client data updated".encode())
    await writer.drain()


async def add_disk(reader, writer):
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


async def get_all_disks(reader, writer):
    # Получаем список всех жестких дисков из базы данных
    cursor.execute("SELECT * FROM disks")
    disks = cursor.fetchall()

    # Отправляем список жестких дисков клиенту
    for disk in disks:
        writer.write(str(disk).encode())
        await writer.drain()


async def authenticate(reader, writer):
    # Получаем данные от клиента
    writer.write('input your login pass:'.encode())
    data = await reader.read(1024)
    message = data.decode()

    # Разбиваем данные на параметры
    params = message.split(',')

    # Проверяем, есть ли клиент с таким ID в базе данных
    cursor.execute("SELECT * FROM clients WHERE id = ?", (params[0],))
    client = cursor.fetchone()

    if client:
        # Если клиент найден, проверяем, правильный ли пароль ввел пользователь
        if params[1] == "password":
            # Если пароль верный, обновляем статус клиента
            # в базе данных на авторизованный
            cursor.execute(
                "UPDATE clients SET authorized = 1 WHERE id = ?",
                (params[0],)
            )
            conn.commit()

            # Отправляем клиенту подтверждение
            writer.write("Authentication successful".encode())
            await writer.drain()
        else:
            # Если пароль неверный, отправляем клиенту сообщение об ошибке
            writer.write("Authentication failed: wrong password".encode())
            await writer.drain()
    else:
        # Если клиент не найден, отправляем клиенту сообщение об ошибке
        writer.write("Authentication failed: client not found".encode())
        await writer.drain()


async def quit(reader, writer):
    # Закрываем соединение с клиентом
    writer.close()
    await writer.wait_closed()


async def handle_connection(reader, writer):
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
                case "add_client":
                    await add_client(reader, writer)
                case "get_all_clients":
                    await get_all_clients(reader, writer)
                case "get_authorized_clients":
                    await get_authorized_clients(reader, writer)
                case "get_all_connected_clients":
                    await get_all_connected_clients(reader, writer)
                case "update_client":
                    await update_client(reader, writer)
                case "add_disk":
                    await add_disk(reader, writer)
                case "get_all_disks":
                    await get_all_disks(reader, writer)
                case "authenticate":
                    await authenticate(reader, writer)
                case "quit":
                    await quit(reader, writer)
                case _:
                    writer.write('Unrecognised command!'.encode())
        except ConnectionError:
            print("Client suddenly closed, cannot send")
            break
    writer.close()
    print("Disconnected by", addr)


async def main(host, port):
    server = await asyncio.start_server(handle_connection, host, port)
    async with server:
        await server.serve_forever()

HOST, PORT = "", 50007

if __name__ == "__main__":
    asyncio.run(main(HOST, PORT))
