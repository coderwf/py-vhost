# -*- coding: utf-8 -*-
# @Time    : 2019-08-18 22:48
# @File    : http_request.py

from requests.utils import requote_uri, unquote
from shared import Reader, Writer, EOF, BufferReader, Buffer


SupportMethods = {"GET", "POST", "PUT", "HEAD", "DELETE", "TRACE"}
SupportVersions = {"HTTP/1.1", "HTTP/1.0"}


class RequestError(Exception):
    pass


class RequestLineError(RequestError):
    pass


class RequestHeaderError(RequestError):
    pass


class RequestValueError(RequestError):
    pass


class Query(dict):
    def __init__(self, params: dict = None):
        dict.__init__(self, params)

    def get_value(self, k, default=None, _typ=None):
        val = self.get(k, default)
        if val is None:
            return val
        return _typ(val) if _typ else val

    def set(self, k, v):
        self[k] = v


class Request:
    def __init__(self):
        # 请求方法
        self._method = None

        # 请求的uri
        self._uri = None

        # http版本
        self._version = None

        # map
        self._headers = None

        # 如果有content则为content的length
        # -1表示请求中没有content-length
        self.content_length = -1
        #
        self.query = Query()

    def to_bytes(self)->bytes:
        buffer = Buffer()
        if self._method is None or self._uri is None or self._version is None:
            raise ValueError("invalid request")

        buffer.write_str("%s " % self.method)
        print(requote_uri(self.uri))
        buffer.write_str("%s " % requote_uri(self.uri))
        buffer.write_str("%s\r\n" % self.version)

        if self._headers is None:
            return buffer.bytes()

        if self.content_length >= 0:
            self._headers["Content-Length"] = self.content_length

        for k, v in self._headers.items():
            buffer.write_str("%s: %s\r\n" % (str(k), str(v)))
        buffer.write_str("\r\n")
        return buffer.bytes()

    @property
    def method(self)->str:
        if self._method is None:
            return ""
        return self._method

    @method.setter
    def method(self, new):
        if new not in SupportMethods:
            raise ValueError("request method must be (%s)" % ",".join(SupportMethods))
        self._method = new

    @property
    def uri(self)->str:
        if self._uri is None:
            return ""
        return self._uri

    @uri.setter
    def uri(self, new):
        if not isinstance(new, str):
            raise ValueError("invalid URI")
        self._uri = new

    @property
    def version(self)->str:
        if self._version is None:
            return ""
        return self._version

    @version.setter
    def version(self, new):
        if new not in SupportVersions:
            raise ValueError("http version must be (%s)" % ",".join(SupportVersions))
        self._version = new

    def header(self, key, _typ=None):
        if self._headers is None:
            return None
        val = self._headers.get(key)
        if val is None or _typ is None:
            return val
        return _typ(val)

    def set_header(self, key, value):
        if self._headers is None:
            self._headers = dict()
        self._headers[key] = value

    @property
    def headers(self):
        if self._headers is None:
            return dict()
        return self._headers.copy()


# 解析请求行
# GET /index HTTP/1.1
def parse_request_line(line)->(str, str, str):
    """

    :param line: request line
    :return: method, uri, version
    """

    items = line.split(" ")
    if len(items) != 3:
        raise RequestLineError(line)
    uri = unquote(items[1])
    return items[0], uri, items[2]


# 解析请求头
def parse_request_headers(line)->(str, str):
    """

    :param line: request header line
    :return: key, value
    """
    loc = line.find(": ")
    if loc == -1:
        raise RequestHeaderError(line)
    k, v = line[: loc], line[loc+2:]
    if len(k) == 0 or len(v) == 0:
        raise RequestHeaderError(line)
    return k, v


class RequestReader(BufferReader):
    def __init__(self, _reader: Reader, chunk_size: int = 1024):
        BufferReader.__init__(self, reader=_reader, chunk_size=chunk_size)

    def read_request(self) -> Request:
        """
        读取一个request
        :return:
        """
        request = Request()

        line = self.read_line()
        request.method, request.uri, request.version = parse_request_line(line)
        header_line = self.read_line()
        while header_line != "":
            k, v = parse_request_headers(header_line)
            request.set_header(k, v)
            header_line = self.read_line()
        cl = request.header("Content-Length", int)
        request.content_length = cl if cl is not None else -1
        return request


def write_request(request: Request, writer: Writer):
    writer.write(request.to_bytes())

