# -*- coding: utf-8 -*-
import socket
from shared import SharedConn, Buffer, EOF, Reader, BufferReader, SocketRW, new_shared_conn


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

    def len(self):
        return len(self._buff)

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
        # content_type 1 bytes 22
        self.content_type = 0
        # tls version 2 bytes
        self.version = 0
        # tls length 2 bytes
        self.length = 0

        # handshake type 1 bytes
        self.handshake_type = 0
        # handshake length 3 bytes
        self.handshake_length = 0
        # handshake version 2 bytes
        self.handshake_version = 0
        # random 32 bytes
        self.random = b""
        # session id length 1 bytes
        self.session_id_len = 0
        # session id session_id_len bytes
        self.session_id = b""
        # cipher suites len 2 bytes
        # 每个加密套件的长度表示为2个字节所以此长度必为偶数
        self.cipher_suites_len = 0
        # cipher suites cipher_suites_len bytes
        self.cipher_suites = b""
        # compression methods len 1 bytes
        self.compression_ml = 0
        # compression methods compression_ml bytes
        self.compression_methods = b""
        # extensions length 2 bytes
        self.extensions_len = 0

        # 每个扩展字段的格式为 Type 2bytes, Length 2bytes, Data Length bytes
        # serverName在扩展字段中
        # 格式为 Type 2 bytes 0x0000
        # Length 2 bytes
        # ListLength 2bytes
        # type 1bytes hostname 为0x0
        # length 2 bytes
        # data length bytes
        self.server_name = ""


def read_client_hello(reader: Reader)->ClientHello:
    """
    读取clientHello
    """
    # 先读header content-type 1 version 2 length 2
    client_hello = ClientHello()
    header_len = 5
    bf = BufferReader(reader)
    header_bytes = bf.read_until_n(header_len)
    client_hello.content_type = header_bytes[0]
    client_hello.version = bytes_to_int(header_bytes[1: 3])
    client_hello.length = bytes_to_int(header_bytes[3: 5])

    content = bf.read_until_n(client_hello.length)

    consumer = Consumer(content)
    client_hello.handshake_type = consumer.consume(1)
    client_hello.handshake_length = consumer.consume(3)
    client_hello.version = consumer.consume(2)

    client_hello.random = consumer.consume(32)
    client_hello.session_id_len = consumer.consume(1)
    client_hello.session_id = consumer.consume(client_hello.session_id_len)
    client_hello.cipher_suites_len = consumer.consume(2)
    client_hello.cipher_suites = consumer.consume(client_hello.cipher_suites_len)
    client_hello.compression_ml = consumer.consume(1)
    client_hello.compression_methods = consumer.consume(client_hello.compression_ml)

    def read_server_name(e_data: bytes):
        e_data = e_data[2:]
        while len(e_data) > 0:
            typ = e_data[0]
            e_data = e_data[1:]
            d_l = bytes_to_int(e_data[: 2])
            e_data = e_data[2:]
            d = e_data[: d_l]
            e_data = e_data[d_l:]
            if typ == 0x0:
                client_hello.server_name = d.decode("utf-8")

    # extensions
    while consumer.len() > 0:
        e_type = consumer.consume(2)
        e_length = consumer.consume(2)
        e_datas = consumer.consume(e_length)
        if e_type != 0x0000:
            continue
        read_server_name(e_datas)

    return client_hello


class TlsConn(SharedConn):
    def __init__(self, _socket: socket.socket, v_buff: Buffer, client_hello: ClientHello):
        SharedConn.__init__(self, _socket, v_buff)
        self.client_hello = client_hello

    def free(self):
        self.client_hello = None

    def server_name(self)->str:
        if self.client_hello is None:
            return ""
        return self.client_hello.server_name


def tls(_socket: socket.socket):
    v_buff, tee = new_shared_conn(_socket)
    client_hello = read_client_hello(tee)
    return TlsConn(_socket, v_buff, client_hello)


if __name__ == "__main__":
    pass
