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


def ensure_bytes(s, encoding='utf-8'):
    if isinstance(s, bytes):
        return s
    return s.encode(encoding)


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
        self._base = basedir
        self._debug = debug
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(sock_path)
        self._wait_prompt()
        if debug:
            self.do_command(b"loglevel 1\r\n")

    def _wait_prompt(self):
        res = BytesIO()
        line = b''
        debug = self._debug

        while True:
            buf = self._sock.recv(512)
            if not buf:
                raise MakuoException("Makuo: socket has closed from remote peer.")
            line += buf
            while b'\n' in line:
                L, line = line.split(b'\n', 1)
                L = L.rstrip()
                if L.startswith(b'error:'):
                    _logger.error(L)
                else:
                    if debug:
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

    def _do_sync_command(self, command, recursive, dry, target, path):
        args = [command]

        if recursive:
            args.append(b'-r')

        if dry:
            args.append(b'-n')

        if target:
            target = ensure_bytes(target, 'ascii')
            args += [b'-t', target]

        if abspath is not None:
            relpath = ensure_bytes(self.relpath(abspath))
            args.append(relpath)

        command = b' '.join(command)
        _logger.info(str(command))
        return self.do_command(command)

    def send(self, abspath, recursive=False, dry=False, target=None):
        return self._do_sync_command(b'send', recursive, dry, target, path)

    def sync(self, abspath, recursive=False, dry=False, target=None):
        return self._do_sync_command(b'sync', recursive, dry, target, path)

    def dsync(self, abspath, recursive=False, dry=False, target=None):
        return self._do_sync_command(b'dsync', recursive, dry, target, path)

    def check(self, abspath, recursive=False, target=None):
        return self._do_sync_command(b'check', recursive, False, target, path)

    def add_exclude(self, pattern):
        return self.do_command(b'exclude add ' + ensure_bytes(pattern))

    def del_exclude(self, pattern):
        return self.do_command(b'exclude del ' + ensure_bytes(pattern))

    def list_exclude(self):
        return self.do_command(b'exclude list')

    def clear_exclude(self):
        return self.do_command(b'exclude clear')

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
