#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

import os
import os.path
import sys
import logging
import traceback
import urlparse
from simiki.compat import is_py2, unicode

try:
    import SimpleHTTPServer as http_server
except ImportError:
    # py3
    import http.server as http_server

try:
    import SocketServer as socket_server
except ImportError:
    # py3
    import socketserver as socket_server

try:
    import urllib2 as urllib_request
except ImportError:
    # py3
    import urllib.request as urllib_request

try:
    from os import getcwdu
except ImportError:
    # py3
    from os import getcwd as getcwdu

URL_ROOT = None
PUBLIC_DIRECTORY = None


class Reuse_TCPServer(socket_server.TCPServer):
    allow_reuse_address = True


class YARequestHandler(http_server.SimpleHTTPRequestHandler):

    def translate_path(self, path):
        """map url path to local file system.
        path and return path are str type

        in py3, builtin translate_path input is str(but it's unicode) and
        return str. so there is no need to do with codecs, system can locate
        file with unicode path.
        in py2, buildin translate_path input is str and return str. we need
        to decode to unicode and then encode path with filesystemencoding(),
        as mentioned above, unicode path can be located, but will have problem
        with py2's translate_path, for uniformity, we also return the
        corresponding type of translate_path in manual part.

        TODO:
          - fspath with os.sep from url always slash
          - URL_ROOT codecs simplify?
          - in the end of if body use super translate_path directly?
        """
        path = urllib_request.unquote(path)
        if not isinstance(path, unicode):
            path = path.decode('utf-8')
        fsenc = sys.getfilesystemencoding()
        if is_py2:
            path = path.encode(fsenc)

        if URL_ROOT and self.path.startswith(URL_ROOT):
            if self.path == URL_ROOT or self.path == URL_ROOT + '/':
                fspath = os.path.join(PUBLIC_DIRECTORY, 'index.html')
                if is_py2:
                    fspath = fspath.encode(fsenc)
            else:
                _url_root = urllib_request.unquote(URL_ROOT)
                if not isinstance(_url_root, unicode):
                    _url_root = _url_root.decode('utf-8')
                if is_py2:
                    _url_root = _url_root.encode(fsenc)
                    fspath = os.path.join(
                        PUBLIC_DIRECTORY.encode(fsenc), path[len(_url_root) + 1:])  # noqa: E501
                else:
                    fspath = os.path.join(
                        PUBLIC_DIRECTORY, path[len(_url_root) + 1:])
            return fspath
        else:
            return http_server.SimpleHTTPRequestHandler \
                .translate_path(self, path)

    def do_GET(self):
        # redirect url
        logging.info('Rquest path: {0}'.format(self.path))

        # Parse query data & params to find out what was passed
        parsedParams = urlparse.urlparse(self.path)

        # Change path to parsed path
        self.path = parsedParams.path

        if URL_ROOT and not self.path.startswith(URL_ROOT):
            self.send_response(301)
            self.send_header('Location', URL_ROOT + self.path)
            self.end_headers()
        http_server.SimpleHTTPRequestHandler.do_GET(self)


def preview(path, url_root, host='127.0.0.1', port=8000):
    """
    :param path: directory path relative to current path
    :param url_root: `root` setted in _config.yml
    """
    global URL_ROOT, PUBLIC_DIRECTORY

    if not host:
        host = '127.0.0.1'
    if not port:
        port = 8000

    if url_root.endswith('/'):
        url_root = url_root[:-1]

    URL_ROOT = urllib_request.quote(url_root.encode('utf-8'))
    PUBLIC_DIRECTORY = os.path.join(getcwdu(), path)

    if os.path.exists(path):
        os.chdir(path)
    else:
        logging.error("Path {} not exists".format(path))
    try:
        Handler = YARequestHandler
        httpd = Reuse_TCPServer((host, port), Handler)
    except (OSError, IOError) as e:
        logging.error("Could not listen on port {0}\n{1}"
                      .format(port, traceback.format_exc()))
        sys.exit(getattr(e, 'exitcode', 1))

    logging.info("Serving at: http://{0}:{1}{2}/".format(host, port, url_root))
    logging.info("Serving running... (Press CTRL-C to quit)")
    try:
        httpd.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutting down server")
        httpd.socket.close()
