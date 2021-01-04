import struct
import io


def send(sock, msg):
    # Prefix each message with a 4-byte length (network byte order)
    msg = struct.pack('>I', len(msg)) + msg
    sock.sendall(msg)


def recv(sock):
    # Read message length and unpack it into an integer
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    return recvall(sock, msglen)


def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    buf = io.BytesIO()
    while buf.tell() < n:
        packet = sock.recv(n - buf.tell())
        if not packet:
            break
        buf.write(packet)
    return buf.getbuffer().tobytes()
