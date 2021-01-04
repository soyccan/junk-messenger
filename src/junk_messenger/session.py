import random
from dataclasses import dataclass

import junk_messenger as jm


@dataclass
class Session:
    sess_id: int
    acct_id: int
    redirect_msg: bytes


class SessionManager:
    def __init__(self, account_manager):
        self.account_manager = account_manager

        # TODO: use queue to provide thread-safety
        # map from sess_id to Session instance
        self.session_list = {}

    def new(self):
        sess_id = random.getrandbits(jm.SESSION_ID_LEN)
        # sess_id = 0 is reserved
        while sess_id in self.session_list or sess_id == 0:
            sess_id = random.getrandbits(jm.SESSION_ID_LEN)
        self.session_list[sess_id] = Session(sess_id=sess_id,
                                             acct_id=0,
                                             redirect_msg=b'')
        return self.session_list[sess_id]

    # def drop(self, sess_id):
    #     del self.session_list[sess_id]

    def get(self, sess_id):
        return self.session_list.get(sess_id)

    def login(self, sess_id, username, password):
        if not self.session_list.get(sess_id):
            return False

        acct = self.account_manager.login(username, password)
        if acct:
            # login accepted
            self.session_list[sess_id].acct_id = acct.id
            return True
        else:
            # login rejected
            return False

    def logout(self, sess_id):
        if not self.session_list.get(sess_id):
            return
        self.session_list[sess_id].acct_id = 0
