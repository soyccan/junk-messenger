import socket
import numpy as np
import cv2
import io
import struct

import utils
from common import *


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(ADDR)
    sock.listen()

    while True:
        print('accept')
        clisock, cliaddr = sock.accept()
        print(clisock, cliaddr)

        while True:
            msg = utils.recv(clisock)
            if not msg:
                print('close', clisock)
                clisock.close()
                break

            shape = struct.unpack('>3I', msg[:12])
            frame = np.frombuffer(msg[12:], dtype='uint8').reshape(shape)

            cv2.imshow('Waaaaa', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()