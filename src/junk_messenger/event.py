import http
import io
import os
import struct
import sys
import threading
import urllib.parse

import cv2

import junk_messenger as jm


LOGIN_FORM = '''
<form action="/login" method="POST">
    <label>User: <input name="username"></label><br>
    <label>Password: <input name="password" type="password"></label><br>
    <button type="submit">Login</button><br>
    <button type="submit" formaction="/register">Register</button><br>
</form>
'''

LOGGED_ACCT = '''
<div>Welcome: {acct}</div>
<a href="/logout">Logout</a>
'''

DEFAULT_BODY = '''
<!DOCTYPE html>
<html>
<h1>WELCOME TO ABYSS!</h1>
<div>Last event: {redirect_msg}</div>
<div>{login_form}</div>
<hr>
{posts}
<hr>
<footer>
    <p>Author: soyccan (B07902143)</p>
    <p>Project Stage 2 of Computer Networking, 2020 Fall, NTU</p>
    <img src="https://4kwallpapers.com/images/wallpapers/macos-big-sur-apple-layers-fluidic-colorful-wwdc-stock-2020-4096x2304-1455.jpg">
</footer>
</html>
'''

POST_BEGIN_FRAG = b'''
<!DOCTYPE html>
<html>
<body>
<h1>POSTS</h1><br>
<a href="/posts">New Post</a>
<main>
'''

POST_FRAG = '''
<article>
<h2>({id}) {title}</h2>
<h3>Author: {author}</h3>
<p>{content}</p>
</article>
<hr>
'''

POST_END_FRAG = b'''
</main>
</body>
</html>
'''

NEW_POST_FORM = '''
<!DOCTYPE html>
<html>
<div>Last event: {redirect_msg}</div>
<div>{login_form}</div>
<form action="/posts" method="post">
<label>Title: <input name="title"></label><br>
<label>Content: <textarea name="content"></textarea></label>
<button type="submit">Post</button>
</form>
</html>
'''


class BaseEvent:
    def __init__(self, reqhdlr):
        self.reqhdlr = reqhdlr
        self.handle()

    def handle(self):
        pass

    def render_login_form(self):
        acct = self.reqhdlr.account
        if acct:
            return LOGGED_ACCT.format(acct=acct.username.decode())
        else:
            return LOGIN_FORM


class DefaultEvent(BaseEvent):
    def handle(self):
        redirect_msg = self.reqhdlr.server.session_manager.get(
                           self.reqhdlr.session.sess_id).redirect_msg.decode()
        if not redirect_msg:
            redirect_msg = ''

        buf = io.BytesIO()
        buf.write(POST_BEGIN_FRAG)
        posts_it = iter(self.reqhdlr.server.post_manager)
        for post in posts_it:
            author = self.reqhdlr.server.account_manager.get(
                     post.author).username.decode()
            buf.write(POST_FRAG.format(
                id=post.id,
                title=post.title.decode(),
                author=author,
                content=post.content.decode()).encode())
        buf.write(POST_END_FRAG)

        body = DEFAULT_BODY.format(login_form=self.render_login_form(),
                                   redirect_msg=redirect_msg,
                                   posts=buf.getvalue().decode())
        self.reqhdlr.send_message(body)


class LoginEvent(BaseEvent):
    def handle(self):
        query = self.reqhdlr.query
        if not query.get(b'username') or not query.get(b'password'):
            self.login_failure()
            return
        accepted = self.reqhdlr.server.session_manager.login(
                    self.reqhdlr.session.sess_id,
                    query[b'username'][0],
                    query[b'password'][0])
        if accepted:
            self.login_success()
        else:
            self.login_failure()

    def login_success(self):
        self.reqhdlr.redirect_to_home('Login success')

    def login_failure(self):
        self.reqhdlr.redirect_to_home('Login fail')


class LogoutEvent(BaseEvent):
    def handle(self):
        self.reqhdlr.server.session_manager.logout(self.reqhdlr.session.sess_id)
        self.reqhdlr.account = None
        self.reqhdlr.redirect_to_home('')

# class ListPostsEvent(BaseEvent):


class NewPostEvent(BaseEvent):
    def handle(self):
        redirect_msg = self.reqhdlr.server.session_manager.get(
                           self.reqhdlr.session.sess_id).redirect_msg.decode()
        if not redirect_msg:
            redirect_msg = ''

        if not self.reqhdlr.account:
            self.reqhdlr.send_message('You should login. <a href="..">Back</a>')
        else:
            self.reqhdlr.send_message(NEW_POST_FORM.format(
                login_form=self.render_login_form(),
                redirect_msg=redirect_msg))


class CreatePostEvent(BaseEvent):
    def handle(self):
        if not self.reqhdlr.account:
            self.fail('You should login')
            return
        acct_id = self.reqhdlr.account.id

        query = self.reqhdlr.query
        title = query.get(b'title')
        content = query.get(b'content')
        if not title or not content:
            self.fail('')
            return
        title = title[0]
        content = content[0]

        suc = self.reqhdlr.server.post_manager.new(title=title,
                                                   author=acct_id,
                                                   content=content)
        if suc:
            self.suceed()
        else:
            self.fail()

    def suceed(self):
        self.reqhdlr.redirect_to_home('')

    def fail(self, msg=''):
        self.reqhdlr.send_message(
            'Fail to create post: ' + msg + '<a href="..">Back</a>',
            http.HTTPStatus.UNPROCESSABLE_ENTITY)


class CreateAccountEvent(BaseEvent):
    def handle(self):
        query = self.reqhdlr.query
        username = query.get(b'username')
        password = query.get(b'password')
        if not username or not password:
            self.fail()
            return
        username = username[0]
        password = password[0]

        suc, msg = self.reqhdlr.server.account_manager.new(username, password)
        if suc:
            self.suceed(msg)
        else:
            self.fail(msg)

    def suceed(self, message):
        self.reqhdlr.redirect_to_home('Account created!')

    def fail(self, message):
        self.reqhdlr.redirect_to_home('Fail to create account: ' + message)


class WatchManagerShowEvent(BaseEvent):
    def handle(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap = cv2.VideoCapture(jm.FALLBACK_VIDEO)
        while True:
            status, frame = cap.read()
            msg = struct.pack('>3I', *frame.shape) + frame.tobytes()
            try:
                jm.utils.send(self.reqhdlr.request, msg)
            except:
                print(sys.exc_info())
                break
        cap.release()

        return


class PlayEvent(BaseEvent):
    def handle(self):
        f = self.reqhdlr.send_head()
        if f:
            try:
                self.reqhdlr.copyfile(f, self.reqhdlr.wfile)
            finally:
                f.close()
