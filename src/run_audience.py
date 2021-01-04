import logging
import socket
import numpy as np
import cv2
import struct

import junk_messenger as jm


def main():
    logging.basicConfig(log_level='DEBUG')

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', 8080))
    sock.sendall(b'GET /play HTTP/1.1\r\n\r\n')

    while True:
        msg = jm.utils.recv(sock)
        if not msg:
            print('close', sock)
            sock.close()
            break

        shape = struct.unpack('>3I', msg[:12])
        frame = np.frombuffer(msg[12:], dtype='uint8').reshape(shape)

        cv2.imshow('Waaaaa', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()