# -*- coding: utf-8 -*-
# @Time    : 2019-08-18 22:48
# @File    : http_request.py


from urllib.parse import unquote
from shared import Reader
from shared import EOF


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
        self.content_length = 0

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


class RequestReader:
    def __init__(self, _reader: Reader, chunk_size: int = 1024):
        self._reader = _reader
        self._buffer = b""
        self._search_loc = 0
        self._chunk_size = chunk_size

    def _fill(self):
        bulk = self._reader.read(self._chunk_size)
        if not bulk:
            raise EOF
        self._buffer += bulk

    def read_line(self, encoding="utf-8")->str:
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

    def _search(self, delimiter)->int:
        loc = self._buffer.find(delimiter, self._search_loc)
        if loc != -1:
            self._search_loc = len(self._buffer)
        return loc

    # 不包括
    def read_delimiter(self, delimiter)->bytes:
        loc = self._search(delimiter)

        while loc == -1:
            self._fill()
            loc = self._search(delimiter)

        # 找到了
        res = self._buffer[:loc+1]
        self._buffer = self._buffer[loc+1:]
        self._search_loc = 0
        return res

    def read_request(self)->Request:
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
        return request



