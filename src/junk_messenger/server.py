import http.server
import http.cookies
import os
import json
import queue
import shutil
import ssl
import sys
import urllib.parse
import threading
import io
import socketserver
import socket

import junk_messenger as jm


class JunkTCPServer(socketserver.TCPServer):
    """ Support HTTPS """
    USE_SSL = True
    CERT_PATH = 'pki/issued/CN PROJECT.crt'
    PRI_KEY_PATH = 'pki/private/CN PROJECT.key'

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        """Constructor.  May be extended, do not override."""
        super().__init__(server_address, RequestHandlerClass)

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.CERT_PATH, self.PRI_KEY_PATH)
        self.socket = socket.socket(self.address_family,
                                    self.socket_type)
        if bind_and_activate:
            try:
                self.server_bind()
                self.server_activate()
                if self.USE_SSL:
                    self.socket = context.wrap_socket(self.socket, server_side=True)
            except:
                self.server_close()
                raise


class JunkHTTPServer(JunkTCPServer):

    allow_reuse_address = 1    # Seems to make sense in testing environment

    def server_bind(self):
        """Override server_bind to store the server name."""
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port


class JunkThreadingHTTPServer(socketserver.ThreadingMixIn, JunkHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)

        self.account_manager = jm.AccountManager()
        self.session_manager = jm.SessionManager(self.account_manager)
        self.post_manager = jm.PostManager()


class JunkHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    # Set this to HTTP/1.1 to enable automatic keepalive
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        self.query = None
        self.account = None
        self.session = None
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.log_request()
        self.do_restful()

    def do_POST(self):
        self.log_request()

        cont_len = self.headers.get('Content-Length')
        if not cont_len:
            return self.send_error(http.HTTPStatus.BAD_REQUEST)
        try:
            cont_len = int(cont_len)
        except ValueError:
            return self.send_error(http.HTTPStatus.BAD_REQUEST)

        req_body = self.rfile.read(cont_len)
        self.query = urllib.parse.parse_qs(req_body)
        self.log_message("query: %s", self.query)
        self.do_restful()

    def do_restful(self):
        cookie = self.headers.get('Cookie')
        print('cookie',cookie)
        if cookie:
            cookie = http.cookies.SimpleCookie(cookie)
            print('cookie',cookie)
            sess_id = cookie.get('session').value
            print('sessio',sess_id)
            if sess_id:
                self.get_session_by_id(sess_id)

        if not self.session:
            self.session = self.server.session_manager.new()
            self.send_response(http.HTTPStatus.TEMPORARY_REDIRECT)
            self.send_session_id()
            self.send_header('Content-Length', '0')
            self.send_header('Location', '/')
            self.end_headers()
            return

        path = urllib.parse.urlsplit(self.path).path.split('/')
        command = self.command.lower()
        if path[1:]:
            event_name = path[1]
            if event_name == 'login':
                jm.LoginEvent(self)
            elif event_name == 'logout':
                jm.LogoutEvent(self)
            elif event_name == 'register':
                if command == 'get':
                    self.redirect_to_home()
                    # jm.NewAccountEvent(self)
                elif command == 'post':
                    jm.CreateAccountEvent(self)
                else:
                    jm.DefaultEvent(self)
            elif event_name == 'posts':
                if command == 'get':
                    jm.NewPostEvent(self)
                    # if not path[2:] or path[2] != 'new':
                    #     jm.ListPostsEvent(self)
                    # else:
                    #     jm.NewPostEvent(self)
                elif command == 'post':
                    jm.CreatePostEvent(self)
                else:
                    jm.DefaultEvent(self)
            else:
                jm.DefaultEvent(self)
        else:
            jm.DefaultEvent(self)

    def send_fileobj(self, fileobj, nbytes, code=http.HTTPStatus.OK):
        self.send_response(code)
        self.send_header("Content-type", 'text/html')
        self.send_header("Content-Length", str(nbytes))
        self.end_headers()
        fileobj.seek(0)
        shutil.copyfileobj(fileobj, self.wfile)

    def send_message(self, message, code=http.HTTPStatus.OK):
        if isinstance(message, str):
            message = message.encode()
        self.send_response(code)
        self.send_header("Content-type", 'text/html')
        self.send_header("Content-Length", str(len(message)))
        self.end_headers()
        self.wfile.write(message)

    def redirect_to_home(self, msg=''):
        if isinstance(msg, str):
            msg = msg.encode()
        self.session.redirect_msg = msg
        self.send_response(http.HTTPStatus.SEE_OTHER)
        self.send_header('Location', '/')
        self.send_header("Content-Length", '0')
        self.end_headers()

    def send_session_id(self):
        hex_sessid = hex(self.session.sess_id)[2:].rjust(jm.SESSION_ID_LEN // 4, '0')
        self.send_header("Set-Cookie", "session=" + hex_sessid)

    def get_session_by_id(self, sess_id):
        sess_id = int.from_bytes(bytes.fromhex(sess_id), 'big')
        self.session = self.server.session_manager.get(sess_id)
        if self.session and self.session.acct_id:
            self.account = self.server.account_manager.get(self.session.acct_id)


def main():
    svr = JunkThreadingHTTPServer(('127.0.0.1', int(sys.argv[1])), JunkHTTPRequestHandler)
    print('Start server')
    svr.serve_forever()


if __name__ == '__main__':
    main()
