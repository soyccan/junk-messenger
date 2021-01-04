import collections
import pickle
import sys

import junk_messenger as jm

Account = collections.namedtuple('Account', ['id', 'username', 'password'])


class AccountManager:
    def __init__(self):
        try:
            print('Loading accounts from', jm.ACCOUNTS_PATH)
            self.accounts_by_id, self.accounts_by_username \
                = pickle.load(open(jm.ACCOUNTS_PATH, 'rb'))
        except:
            print(sys.exc_info())
            self.accounts_by_id = {}
            self.accounts_by_username = {}
        self.counter = 0

    def new(self, username, password):
        valid = (isinstance(username, bytes)
                 and len(username) < 100
                 and isinstance(password, bytes)
                 and len(password) < 100)
        if not valid:
            return False, 'invalid username or password'

        acct_exist = self.accounts_by_username.get(username)
        if acct_exist:
            return False, 'account exists'

        while self.accounts_by_id.get(self.counter) or self.counter == 0:
            # id = 0 is reserved
            self.counter += 1
        acct = Account(
                id=self.counter,
                username=username,
                # password_md5=hashlib.md5(password).digest(),
                password=password)
        self.accounts_by_id[self.counter] = acct
        self.accounts_by_username[username] = acct
        self.counter += 1
        self.save()
        return True, ''

    # def drop(self, account_id):
    #     del self.accounts_by_id[account_id]

    def get(self, account_id):
        return self.accounts_by_id.get(account_id)

    def get_by_name(self, name):
        return self.accounts_by_username.get(name)

    def __len__(self):
        return len(self.accounts_by_id)

    def __iter__(self):
        return iter(self.accounts_by_id.values())

    def save(self):
        print('Saving accounts to', jm.ACCOUNTS_PATH)
        pickle.dump((self.accounts_by_id, self.accounts_by_username),
                    open(jm.ACCOUNTS_PATH, 'wb'))

    def login(self, username, password):
        acct = self.accounts_by_username.get(username)
        # if acct and acct.password_md5 == hashlib.md5(password):
        if acct and acct.password == password:
            return acct
        else:
            return None
