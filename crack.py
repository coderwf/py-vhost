# -*- coding: utf-8 -*-
# @Time    : 2019-08-20 23:58
# @File    : crack.py
import socket
from shared import Conn, Buffer, SocketRW
from http_request import RequestReader, Request


class CrackConn(Conn):
    def __init__(self, _socket: socket.socket, request_handler=None):
        """

        :param _socket:
        :param request_handler:
        """
        """
        1.用request_reader不断读取完整的request并用request_handler进行处理
        并将处理后的request放入v_buffer中,后续读取的body也存入v_buffer中
        2.每次读取先从v_buffer中读取,读到则直接返回,否则进行第一步
        3.body采取分段读取
        """
        # 第一个request
        self._request_handler = request_handler
        self._v_buff = Buffer()
        self._request_reader = RequestReader(SocketRW(_socket), 512)
        self._read_error = None
        self._body_len = 0
        Conn.__init__(self, _socket)
        self.request = self._read_request()

    def set_request_handler(self, request_handler):
        self._request_handler = request_handler

    def recv(self, buff_size: int, flags: int = 0):
        if self._v_buff.len() > 0:
            return self._v_buff.read(buff_size)

        self._read_full_request()
        return self._v_buff.read()

    def _read_full_request(self):
        """
        body没读取完则继续读取body
        :return:
        """
        if self._body_len > 0:
            self._read_request_body()
            return
        self._read_request()

    def _read_request(self)->Request:
        req = self._request_reader.read_request()
        self.request = req
        self._body_len = req.content_length
        if self._request_handler:
            req = self._request_handler(req)
            req.content_length = self._body_len
        self._v_buff.write(req.to_bytes())
        return req

    def _read_request_body(self):
        # 每次只读取512字节
        read_body_size = 512
        if read_body_size > self._body_len:
            read_body_size = self._body_len
        chunk = self._request_reader.read_until_n(read_body_size)
        self._v_buff.write(chunk)
        self._body_len -= read_body_size


"""
def request_handler(req: Request)->Request:
    return req
"""


def crack(s: socket.socket, request_handler=None)->CrackConn:
    return CrackConn(s, request_handler)



