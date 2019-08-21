# -*- coding: utf-8 -*-
import socket
from http_request import Request, RequestReader
from shared import SharedConn, new_shared_conn, Buffer


class HttpConn(SharedConn):
    def __init__(self, request: Request, v_buff: Buffer, _socket: socket.socket):
        SharedConn.__init__(self, _socket, v_buff)
        self.request = request

    def free(self):
        self.request = None


def http(_socket: socket.socket)->HttpConn:
    v_buff, tee = new_shared_conn(_socket)
    r_reader = RequestReader(tee)
    return HttpConn(r_reader.read_request(), v_buff, _socket)

