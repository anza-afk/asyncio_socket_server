import socket
# import psutil


HOST, PORT = "", 50007
# total_memory = list(psutil.cpu_stats())

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

    sock.connect((HOST, PORT))
    sock.settimeout(3)
    test_data = '256,4,1'  # надо тянуть данные
    while True:
        # total, _, _ = psutil.disk_usage("/")
        # total_gb = total // (2**30)
        data = input("Type the message to send:")
        data_bytes = data.encode()  # str to bytes
        sock.sendall(data_bytes)
        try:
            data_bytes = sock.recv(1024)
            data = data_bytes.decode()
            if data in ("Successful authentication",
                        'Succsessful registration!'):
                print("Received:", data)
                print(f'sending data {test_data}')
                sock.sendall(test_data.encode())
                data_bytes = sock.recv(1024)
                data = data_bytes.decode()
                print("Received:", data)
            else:
                print("Received:", data)
        except TimeoutError:
            print("Timeout error")
            continue
