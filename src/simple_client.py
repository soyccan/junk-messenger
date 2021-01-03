import socket
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
context = ssl.create_default_context()

with socket.create_connection(('127.0.0.1', 8080)) as sock:
    # with context.wrap_socket(sock, server_hostname='127.0.0.1') as ssock:
    ssock = sock

    while True:
        ssock.send(b'GET / HTTP/1.1\r\n')
        ssock.send(b'Connection: keep-alive\r\n')
        ssock.send(b'\r\n')

        buf = ssock.recv(1024)
        # print(buf)
