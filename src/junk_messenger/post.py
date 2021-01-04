import collections
import pickle
import sys

import junk_messenger as jm

Post = collections.namedtuple('Post', ['author', 'content', 'title', 'id'])


class PostManager:
    def __init__(self):
        try:
            print('Loading posts from', jm.POSTS_PATH)
            self.posts = pickle.load(open(jm.POSTS_PATH, 'rb'))
        except:
            print(sys.exc_info())
            self.posts = {}
        self.counter = 0

    def new(self, author, title, content):
        valid = (isinstance(author, int)
                 and isinstance(title, bytes)
                 and len(title) < 100
                 and isinstance(content, bytes)
                 and len(content) < 10000)
        if not valid:
            return False

        while self.posts.get(self.counter):
            self.counter += 1
        self.posts[self.counter] = Post(author=author,
                                        title=title,
                                        content=content,
                                        id=self.counter)
        self.counter += 1
        self.save()
        return True

    def drop(self, post_id):
        del self.posts[post_id]

    def get(self, post_id):
        return self.posts[post_id]

    def __len__(self):
        return len(self.posts)

    def __iter__(self):
        return iter(self.posts.values())

    def save(self):
        print('Saving posts to', jm.POSTS_PATH)
        pickle.dump(self.posts, open(jm.POSTS_PATH, 'wb'))