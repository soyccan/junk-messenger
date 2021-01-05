from junk_messenger.account import AccountManager
from junk_messenger.event import (
    LoginEvent, DefaultEvent, CreateAccountEvent,
    NewPostEvent, CreatePostEvent, LogoutEvent, PlayEvent
)
from junk_messenger.server import JunkThreadingHTTPServer, JunkHTTPRequestHandler
from junk_messenger.post import PostManager
from junk_messenger.session import SessionManager
from junk_messenger import utils

SESSION_ID_LEN = 64
POSTS_PATH = 'db/posts.pkl'
ACCOUNTS_PATH = 'db/accounts.pkl'
CERT_PATH = 'pki/issued/CN PROJECT.crt'
PRI_KEY_PATH = 'pki/private/CN PROJECT.key'
TS_PATH = 'ts/'
FFMPEG_BIN = '/usr/local/bin/ffmpeg'
FALLBACK_VIDEO = 'video/00018.mp4'
