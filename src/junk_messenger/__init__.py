from junk_messenger.event import (
    LoginEvent, DefaultEvent, CreateAccountEvent,
    NewPostEvent, CreatePostEvent, LogoutEvent
)
from junk_messenger.post import PostManager
from junk_messenger.account import AccountManager
from junk_messenger.session import SessionManager

SESSION_ID_LEN = 64
POSTS_PATH = 'db/posts.pkl'
ACCOUNTS_PATH = 'db/accounts.pkl'
