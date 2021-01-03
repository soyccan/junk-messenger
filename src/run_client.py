import cv2
import time
from PIL import Image
import socket
import av
import struct

import utils
from common import *


class MultimediaServer:
    def __init__(self):
        pass

    def run(self):
        pass


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(ADDR)

    cap = cv2.VideoCapture('../video/00018.MTS')
    # cap = av.open(format='avfoundation', file='0')
    # cap = av.open('../video/00018.MTS')

    # for frame in cap.decode(video=0):
        # We need to skip the "flushing" packets that `demux` generates.
        # if not packet.dts:
        #     continue

    while True:
        status, frame = cap.read()
        arr = frame #.to_ndarray()
        msg = struct.pack('>3I', *arr.shape) + arr.tobytes()
        utils.send(sock, msg)

        # for frame in packet.decode():
        #     frame.pts = None
        #     print(len(data))

    # for packet in cap.demux(video=0):
        # status, frame = cap.read()

        # if packet.dts is None:
        #     continue
        #
        # data = packet.to_bytes()
        # print(len(data))
        # sock.sendto(data, ADDR)
        # for i in range(0, len(data), CHUNK_SIZE):
        #     seg = data[i: i+CHUNK_SIZE]
        #     sock.sendto(seg, ADDR)

        #  imgArray = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        #  image = Image.fromarray(imgArray)
        #  photo = ImageTk.PhotoImage(image=image)
        #
        #  # 建立承載RTSP影像串流的容器物件
        #  window = tk.Label(bg="black", image=photo, width=320, height=240)
        #
        #  # avoid garbage collection(避免資源被回收)(把圖片註冊到物件中，並自訂屬性，避免被回收)
        #  window.rtspImage = photo
        #
        #  # 放置在畫面上
        #  window.place(x=0, y=0, anchor='nw')

        # cv2.imshow('Wahaa', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
