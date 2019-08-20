# -*- coding: utf-8 -*-
import socket
from shared import SharedConn, Buffer


class ClientHello:
    def __init__(self):
        pass


class TlsConn(SharedConn):
    def __init__(self, _socket: socket.socket, v_buff: Buffer):
        SharedConn.__init__(self, _socket, v_buff)


def Tls(_socket: socket.socket):
    pass
