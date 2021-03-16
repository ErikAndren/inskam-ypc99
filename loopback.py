import socket
import binascii
BUFFER_SIZE = 16384

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("Binding " + socket.gethostname())
sock.bind((socket.gethostname(), 80))
sock.listen(1)

while True:
    (client_sock, address) = sock.accept()
    print(address, " connected")
    data = client_sock.recv(BUFFER_SIZE)
    print(binascii.hexlify(data))
    client_sock.send(data)
