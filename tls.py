# -*- coding: utf-8 -*-
import socket
from shared import SharedConn, Buffer


class Consumer:
    def __init__(self, init_bytes=b""):
        self._buff = init_bytes

    def consume(self):
        pass

    def write(self, chunk: bytes):
        pass

    
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
