import http.cookies
import http.server
import os
import shutil
import signal
import socket
import socketserver
import ssl
import subprocess
import sys
import time
import urllib.parse
import threading
import ffmpeg_streaming as ffstream
import struct
import io

import junk_messenger as jm


class JunkTCPServer(socketserver.TCPServer):
    """ Support HTTPS """
    USE_SSL = True

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        """Constructor.  May be extended, do not override."""
        super().__init__(server_address, RequestHandlerClass)

        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.load_cert_chain(jm.CERT_PATH, jm.PRI_KEY_PATH)
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

        self.stream_proc = None
        self.stream_thread = None

    def __del__(self):
        self.stop_streaming()

    def run_streaming(self):
        cmd = [jm.FFMPEG_BIN,
               '-y',
               '-f', 'avfoundation',
               '-framerate', '30',
               '-i', '0',
               '-c:v', 'libx264',
               '-c:a', 'aac',
               '-tune', 'zerolatency',
               '-bf', '1',
               '-keyint_min', '25',
               '-g', '250',
               '-sc_threshold', '40',
               '-hls_list_size', '10',
               '-hls_time', '5',
               '-hls_allow_cache', '1',
               '-hls_segment_filename', 'play/stream_%04d.ts',
               '-hls_fmp4_init_filename', 'stream_init.mp4',
               '-s:v', '854x480',
               '-b:v', '750k',
               '-b:a', '192k',
               '-strict', '-2',
               '-hls_flags', 'delete_segments',
               'play/stream.m3u8']
        self.stream_proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def start_streaming(self):
        try:
            os.remove('play/stream.m3u8')
        except:
            pass

        self.stream_thread = threading.Thread(target=self.run_streaming())
        self.stream_thread.run()

        while not os.path.exists('play/stream.m3u8'):
            time.sleep(1)

        # _480p = ffstream.Representation(ffstream.Size(854, 480),
        #                                 ffstream.Bitrate(750 * 1024, 192 * 1024))
        # video = ffstream.input('0', capture=True, f='avfoundation', framerate='30')
        # if not video:
        #     # if no webcam is found
        #     video = ffstream.input('video/00018.MTS')
        # hls = video.hls(ffstream.Formats.h264(), hls_list_size=10, hls_time=5)
        # hls.flags('delete_segments')
        # hls.representations(_480p)
        # hls.output('play/stream.m3u8',
        #            ffmpeg_bin=jm.FFMPEG_BIN,
        #            async_run=False)
        #

    def stop_streaming(self):
        pass
        # if self.stream_proc:
        #     os.kill(self.stream_proc.pid, signal.SIGTERM)
        #     os.waitpid(self.stream_proc.pid, 0)
        #     self.stream_proc = None
        #     try:
        #         os.remove('play/stream.m3u8')
        #     except:
        #         pass


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
        qs = urllib.parse.urlsplit(self.path).query
        qs = urllib.parse.unquote_to_bytes(qs)
        self.query = urllib.parse.parse_qs(qs)
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
        path = urllib.parse.urlsplit(self.path).path.split('/')
        if not path[1:]:
            jm.DefaultEvent(self)
            return
        event_name = path[1]
        command = self.command.lower()

        # play event require no session, otherwise players like VLC won't work
        if event_name == 'play':
            jm.PlayEvent(self)
            return

        cookie = self.headers.get('Cookie')
        if cookie:
            cookie = http.cookies.SimpleCookie(cookie)
            sess_id = cookie.get('session').value
            if sess_id:
                self.get_session_by_id(sess_id)

        if not self.session:
            self.session = self.server.session_manager.new()
            self.send_response(http.HTTPStatus.TEMPORARY_REDIRECT)
            self.send_session_id()
            self.send_header('Content-Length', '0')
            self.send_header('Location', self.path)
            self.end_headers()
            return

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
        # elif event_name == 'stream':
        #     jm.StreamEvent(self)
        elif event_name == 'play':
            jm.PlayEvent(self)
        else:
            jm.DefaultEvent(self)

    def send_fileobj(self, fileobj, nbytes,
                     mimetype='text/html', code=http.HTTPStatus.OK):
        self.send_response(code)
        self.send_header("Content-type", mimetype)
        self.send_header("Content-Length", str(nbytes))
        self.end_headers()
        shutil.copyfileobj(fileobj, self.wfile)

    def send_message(self, message,
                     mimetype='text/html', code=http.HTTPStatus.OK):
        if isinstance(message, str):
            message = message.encode()
        self.send_response(code)
        self.send_header("Content-type", mimetype)
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
