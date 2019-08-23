# -*- coding: utf-8 -*-
# @Time    : 2019-08-21 17:19
# @File    : proxy.py

import socket
import threading
from shared import Conn, io_copy
from http_conn import http
from crack import crack
from http_request import Request


class Pipe(threading.Thread):
    def __init__(self, from_conn: Conn, to_conn: Conn):
        self.from_conn = from_conn
        self.to_conn = to_conn
        threading.Thread.__init__(self)
        self.from_bytes = 0

    def run(self):
        try:
            self.from_bytes = io_copy(self.from_conn, self.to_conn)
        except Exception as e:
            print(e)


class HandlerConn(threading.Thread):
    def __init__(self, s: socket.socket, get_proxy_func):
        threading.Thread.__init__(self)
        self._socket = s
        self.get_proxy_func = get_proxy_func

        self.from_bytes, self.to_bytes = 0, 0

    def wrap_conn(self):
        return http(self._socket)

    def run(self):
        try:
            http_conn = self.wrap_conn()
            request = http_conn.request
            proxy = self.get_proxy_func(request)
            if proxy is None:
                raise Exception("get proxy is none")
        except Exception as e:
            print("get proxy failed cause: %s" % e)
            self._socket.close()
            return

        proxy = Conn(proxy)
        # make pipe
        p1 = Pipe(http_conn, proxy)
        p2 = Pipe(proxy, http_conn)
        # set daemon
        p1.setDaemon(True)
        p2.setDaemon(True)
        # start and join
        p1.start()
        p2.start()
        p1.join()
        p2.join()
        # close conn
        http_conn.close()
        proxy.close()

        from_addr = ":".join(http_conn.socket.getpeername())
        to_addr = ":".join(proxy.socket.getpeername())
        # logging
        print("%d(from), %d(to) bytes copied between %s and %s before break" % (p1.from_bytes, p2.from_bytes, from_addr,
                                                                                to_addr))


class HandleCrackConn(HandlerConn):
    def __init__(self, s: socket.socket, get_proxy_func, request_handler=None):
        HandlerConn.__init__(self, s, get_proxy_func)
        self.request_handler = request_handler

    def wrap_conn(self):
        return crack(self._socket, self.request_handler)


class Proxy:
    def __init__(self, get_proxy, server_host="127.0.0.1", server_port=9999, backlog=5):
        """
       
        :param get_proxy: 获取proxy方法,第一个参数默认为request
        :param server_host: 服务监听地址
        :param server_port: 服务监听端口
        """""
        self.get_proxy = get_proxy
        self.backlog = backlog
        self.server_addr = (server_host, server_port)
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def __del__(self):
        if self._server_socket is not None:
            self._server_socket.close()

    def _handler_conn(self, client_s: socket.socket):
        return HandlerConn(client_s, self.get_proxy)

    def _accept(self):
        client_s, _ = self._server_socket.accept()
        print("-----------accept connection from %s ------------" % str(client_s.getpeername()))
        handler_thread = self._handler_conn(client_s)
        handler_thread.setDaemon(True)
        handler_thread.start()

    def listen_and_accept(self):

        if self._server_socket is None:
            raise Exception("server has not init")

        self._server_socket.bind(self.server_addr)
        print("server listen at: %s: %d" % (self.server_addr[0], self.server_addr[1]))
        self._server_socket.listen(self.backlog)

        try:
            while True:
                self._accept()
        except Exception as e:
            print("server failed with %s , closing" % e)
        finally:
            if self._server_socket:
                self._server_socket.close()
                self._server_socket = None

    def start(self):
        self.listen_and_accept()


class CrackProxy(Proxy):
    def __init__(self, get_proxy, server_host="127.0.0.1", server_port=9999, backlog=5, request_handler=None):
        Proxy.__init__(self, get_proxy, server_host, server_port, backlog)
        self.request_handler = request_handler

    def _handler_conn(self, client_s: socket.socket):
        return HandleCrackConn(client_s, self.get_proxy, self.request_handler)


def gen_proxy(request: Request)->socket.socket:
    print(request.method, request.uri, request.version, request.headers)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("x.x.x.x", 80))
    return s


def request_handler(request: Request) ->Request:
    uri = request.uri
    loc = uri.find("?")
    if loc == -1:
        request.uri = "/form"
    else:
        request.uri = "/form?%s" % uri[loc+1:]
    return request


if __name__ == "__main__":
    CrackProxy(gen_proxy, server_port=9999, request_handler=request_handler).start()
