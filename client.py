import socket
import psutil

HOST, PORT = "", 50007
total_memory = list(psutil.cpu_stats())

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((HOST, PORT))
    while True:
        total, _, _ = psutil.disk_usage("/")
        total_gb = total // (2**30)
        data = input("Type the message to send:")
        data_bytes = data.encode()  # str to bytes
        sock.sendall(data_bytes)
        data_bytes = sock.recv(1024)
        print(total_gb)
        data = data_bytes.decode()  # bytes to str
        print("Received:", data)
