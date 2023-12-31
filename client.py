import asyncio

import os

from dotenv import load_dotenv

load_dotenv()

HOST = os.environ["CLIENT_HOST"]
PORT = os.environ["SERVER_PORT"]


async def run_client() -> None:
    reader, writer = await asyncio.open_connection("localhost", PORT)
    while True:
        message = input("Type the message to send:")
        data_bytes = message.encode()
        writer.write(data_bytes)
        await writer.drain()
        try:
            data_bytes = await reader.read(1024)
            if not data_bytes:
                raise Exception('Socket not communicating with the client')
            data = data_bytes.decode()
            print("Received:", data)
        except TimeoutError:
            print("Timeout error")
            continue

        if (message == 'quit'):
            writer.write(data_bytes)
            writer.close()
            break


if __name__ == '__main__':
    try:
        asyncio.run(run_client(), debug=False)
    except RuntimeError:
        print('Client closed')
        pass
