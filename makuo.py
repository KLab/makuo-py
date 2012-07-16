# -*- coding: utf-8 -*-
"""
    makuo
    ~~~~~

    `makuosan <http://lab.klab.org/wiki/Makuosan>` client.
"""

import socket
import os
import logging

try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

_logger = logging.getLogger(__name__)


class MakuoException(Exception):
    pass

class Makuo(object):
    """
    Makuosan client.
    """

    def __init__(self, sock_path, basedir, debug=False):
        """
        `sock_path` is path of Unix domain socket that makuosan daemon listens.

        `basedir` is base directory that makuosan works.

        When `debug` is true, set makuosan loglevel to 1.
        """
        self._debug = debug
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(sock_path)
        self._base = basedir
        self._wait_prompt()
        if debug:
            self.do_command(b"loglevel 1\r\n")

    def _wait_prompt(self):
        res = BytesIO()
        line = b''
        while True:
            buf = self._sock.recv(512)
            if not buf:
                raise MakuoException("Makuo: socket has closed from remote peer.")
            line += buf
            while b'\n' in line:
                L, line = line.split(b'\n', 1)
                L = L.rstrip()
                if L.startswith(b'error:'):
                    raise MakuoException(L)
                if self._debug:
                    _logger.debug(L)
                res.write(L + b'\n')
            if line == b'> ':
                return res.getvalue()

    def relpath(self, abspath):
        relpath = os.path.relpath(abspath, self._base)
        if not isinstance(relpath, bytes):
            relpath = relpath.encode('utf-8')
        return relpath

    def do_command(self, command):
        """Send `command`"""
        self._sock.sendall(command + b'\r\n')
        return self._wait_prompt()

    def send(self, abspath):
        relpath = self.relpath(abspath)
        _logger.info("Sending file: %r", relpath)
        return self.do_command(b'send -r {0}'.format(relpath))

    def send_dir(self, abspath):
        relpath = self.relpath(abspath)
        _logger.info("Sending dir: %r", relpath)
        self.do_command(b'dsync -r {0}'.format(relpath))
        self.do_command(b'send -r {0}'.format(relpath))

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
