# -*- coding: utf-8 -*-
import socket


class EOF(Exception):
    pass


class Reader:
    def read(self, chunk_size)->bytes:
        pass


class Writer:
    def write(self, bs: bytes):
        pass


class SocketRW(Reader, Writer):
    def __init__(self, _socket: socket.socket):
        self._socket = _socket

    def read(self, chunk_size) ->bytes:
        chunk = self._socket.recv(chunk_size)
        if not chunk:
            raise EOF
        return chunk

    def write(self, bs: bytes):
        while len(bs) > 0:
            n = self._socket.send(bs)
            bs = bs[n:]


class Conn:
    def __init__(self, _socket: socket.socket):
        self._socket = _socket

    @property
    def socket(self):
        return self._socket

    def recv(self, buff_size: int, flags: int = 0):
        return self._socket.recv(buff_size, flags)

    def send(self, data: bytes, flags: int = 0):
        return self._socket.send(data, flags)

    def sendall(self, data: bytes, flags: int = 0):
        return self._socket.sendall(data, flags)

    def setblocking(self, flag: bool):
        return self._socket.setblocking(flag)

    def shutdown(self, how: int):
        return self._socket.shutdown(how)

    def close(self):
        return self._socket.close()


class Buffer(Reader, Writer):
    def __init__(self, init_bytes=b""):
        self._buff = init_bytes

    def read(self, chunk_size=1024):
        if len(self._buff) == 0:
            raise EOF
        chunk = self._buff[: chunk_size]
        self._buff = self._buff[chunk_size:]
        return chunk

    def write(self, bs: bytes):
        self._buff += bs


class TeeReader(Reader):
    def __init__(self, reader: Reader, writer: Writer):
        self.reader = reader
        self.writer = writer

    def read(self, chunk_size):
        chunk = self.reader.read(chunk_size)
        if not chunk:
            raise EOF
        self.writer.write(chunk)
        return chunk


class SharedConn(Conn):
    def __init__(self, _socket: socket.socket, v_buff: Buffer):
        Conn.__init__(self, _socket)
        self._v_buff = v_buff

    def recv(self, buff_size: int, flags: int = 0):
        if self._v_buff is None:
            return self._socket.recv(buff_size, flags)

        read = b""

        try:
            read += self._v_buff.read(chunk_size=buff_size)
        except EOF:
            read += self._socket.recv(buff_size - len(read), flags)
            self._v_buff = None

        return read


def new_shared_conn(s: socket.socket) ->(Buffer, TeeReader):
    v_buff = Buffer()
    s_reader = SocketRW(s)

    tee = TeeReader(s_reader, v_buff)
    return v_buff, tee
