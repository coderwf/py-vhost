# -*- coding: utf-8 -*-
import socket


class EOF(Exception):
    pass


class Reader:
    def read(self, chunk_size)->bytes:
        pass


class Writer:
    def write(self, bs: bytes)->int:
        pass


class ReaderWriter(Reader, Writer):
    pass


class SocketRW(Reader, Writer):
    def __init__(self, _socket: socket.socket):
        self._socket = _socket

    def read(self, chunk_size) ->bytes:
        chunk = self._socket.recv(chunk_size)
        if not chunk:
            raise EOF
        return chunk

    def write(self, bs: bytes)->int:
        while len(bs) > 0:
            n = self._socket.send(bs)
            bs = bs[n:]
        return len(bs)


class Conn(ReaderWriter):
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

    def read(self, chunk_size)->bytes:
        return self.recv(chunk_size)

    def write(self, bs: bytes)->int:
        return self.send(bs)


class Buffer(Reader, Writer):
    def __init__(self, init_bytes=b""):
        self._buff = init_bytes

    def len(self):
        return len(self._buff)

    def read(self, chunk_size=1024):
        if len(self._buff) == 0:
            raise EOF
        chunk = self._buff[: chunk_size]
        self._buff = self._buff[chunk_size:]
        return chunk

    def write(self, bs: bytes):
        self._buff += bs

    def write_str(self, s: str, encoding="utf-8"):
        self._buff += s.encode(encoding=encoding)

    def bytes(self):
        return self._buff


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


class BufferReader:
    def __init__(self, reader: Reader, chunk_size=1024):
            self._reader = reader
            self._buffer = b""
            self._search_loc = 0
            self._chunk_size = chunk_size

    def _fill(self):
        bulk = self._reader.read(self._chunk_size)
        if not bulk:
            raise EOF
        self._buffer += bulk

    def read_line(self, encoding="utf-8") -> str:
        """
        读取直到\n
        返回不包括\n如果前一个为\r则\r也不包括
        :return:
        """
        line = self.read_delimiter(delimiter=b"\n")
        line = line[: -1]

        # 13 == "\r"
        if len(line) > 0 and line[-1] == 13:
            line = line[: -1]
        return line.decode(encoding=encoding)

    def _search(self, delimiter) -> int:
        loc = self._buffer.find(delimiter, self._search_loc)
        if loc != -1:
            self._search_loc = len(self._buffer)
        return loc

    # 不包括
    def read_delimiter(self, delimiter: bytes) -> bytes:
        loc = self._search(delimiter)

        while loc == -1:
            self._fill()
            loc = self._search(delimiter)

        # 找到了
        res = self._buffer[:loc + 1]
        self._buffer = self._buffer[loc + 1:]
        self._search_loc = 0
        return res

    def read_until_n(self, n: int)->bytes:
        """
        一共直到读取n个字节
        当缓存buffer长度小于n则需要从reader中读取填充直到buffer长度不小于n
        :return:
        """
        while len(self._buffer) < n:
            self._fill()
        chunk = self._buffer[: n]
        self._buffer = self._buffer[n:]
        return chunk


def new_shared_conn(s: socket.socket) ->(Buffer, TeeReader):
    v_buff = Buffer()
    s_reader = SocketRW(s)

    tee = TeeReader(s_reader, v_buff)
    return v_buff, tee


def io_copy(src: Conn, target: Conn, r_flags=0, s_flags=0)->int:
    """
    从src中读取数据并放入到target中,返回一共读取的字节数
    :param src:
    :param target:
    :param r_flags:
    :param s_flags:
    :return:
    """
    copied = 0

    while True:
        chunk = src.recv(1024, flags=r_flags)
        if not chunk:
            return copied
        while chunk:
            n = target.send(chunk, flags=s_flags)
            copied += n
            chunk = chunk[n:]
