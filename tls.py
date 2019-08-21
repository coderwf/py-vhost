# -*- coding: utf-8 -*-
import socket
from shared import SharedConn, Buffer, EOF


def bytes_to_int(chunk: bytes) ->int:
    if len(chunk) == 0:
        raise ValueError("chunk cant be empty")
    num = 0
    for b in chunk:
        num <<= 8
        num |= b
    return num


class Consumer:
    def __init__(self, init_bytes=b""):
        self._buff = init_bytes

    def consume(self, n)->bytes:
        if len(self._buff) < n:
            raise EOF
        c = self._buff[: n]
        self._buff = self._buff[n:]
        return c

    def consume_int(self, n)->int:
        chunk = self.consume(n)
        return bytes_to_int(chunk)

    def write(self, chunk: bytes):
        self._buff += chunk


class ClientHello:
    def __init__(self):
        pass


class TlsConn(SharedConn):
    def __init__(self, _socket: socket.socket, v_buff: Buffer):
        SharedConn.__init__(self, _socket, v_buff)

    def free(self):
        pass


def tls(_socket: socket.socket):
    pass


if __name__ == "__main__":
    pass