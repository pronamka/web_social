from datetime import datetime
from abc import ABC
from typing import Union

from server.database import DataBase
from server.posts import UserPostRegistry, CommentsRegistry


class Manager(ABC):
    def __init__(self, access_level: int = 1) -> None:
        self.database = DataBase(access_level=access_level)


class BasicManager(ABC):
    database = DataBase(access_level=1)


class UserManager(Manager):
    """Manager for working with user properties"""

    def __init__(self, user_id: int, access_level: int) -> None:
        super().__init__(access_level)
        self.user_id = user_id


class PostManager(Manager):
    """Manager for creating or deleting posts"""

    def create_post(self, user_id: int, post_title: str) -> None:
        query = "INSERT INTO posts (user_id, title, date) VALUES (?, ?, ?);"
        data_package = (user_id, post_title, datetime.now().strftime("%A, %d. %B %Y %I:%M%p"))
        self.database.insert(query, data_package)

    def delete_post(self, post_id: int) -> None:
        self.database.delete(f"""DELETE FROM posts WHERE post_id='{post_id}'""")


class UserPostManager(UserManager):
    """Registry containing all post of a specific user"""
    # it's now made so this class has too many
    # responsibilities: both over posts and comments.
    # An effective way of separating them without
    # violating DRY should be found

    comment_belonging_request = "WITH p_id AS (SELECT post_id FROM comments WHERE comment_id == " \
                                "{comment_id}) SELECT user_id FROM posts WHERE post_id IN p_id"

    def __init__(self, user_id: int, *args) -> None:
        super(UserPostManager, self).__init__(user_id, 4)
        self.posts = {}
        self.post_ids = []
        self.comments = {}
        self.post_manger = PostManager(4)
        self.count = 0
        self.post_amount = 0
        self.comments_amount = 0

    def get_latest_posts(self, amount: int, start_with: int, post_type: int = 1) -> list:
        res = UserPostRegistry.get_posts(amount, start_with, {'of_user': self.user_id}, post_type=post_type)
        return res

    def get_latest_comments(self, amount: int, start_with: int, status) -> list:
        return CommentsRegistry.fetch_comments_on_users_post(amount, start_with, self.user_id, status)

    def get_overall_amounts(self, objects):
        r = {'comments': 'comments', 'views': 'post_views', 'likes': 'post_likes'}
        post_ids = self.database.get_all_singles(f'SELECT post_id FROM posts WHERE user_id={self.user_id}')
        post_ids = tuple(post_ids) if len(post_ids) != 1 else f'({post_ids[0]})'
        info = {}
        for i in objects:
            info[i] = self.database.get_all_singles(f'SELECT COUNT(user_id) FROM {r.get(i, "views")} '
                                                    f'WHERE post_id IN {post_ids}')
        return info

    def get_post_amount(self) -> int:
        posts = self.database.get_information(f'SELECT COUNT(DISTINCT post_id) FROM posts '
                                              f'WHERE user_id="{self.user_id}"')
        return posts

    def get_comments_amount(self, post_id: int) -> tuple:
        comments = self.database.get_information(f'SELECT COUNT(DISTINCT comment_id) FROM comments '
                                                 f'WHERE post_id="{post_id}"')
        return comments

    def get_post(self, post_id: int) -> Union[bool, tuple]:
        post = self.database.get_information(f'SELECT title, tags FROM posts '
                                             f'WHERE post_id={post_id} AND user_id={self.user_id}')
        if not post:
            return False
        return post

    def check_comment_belonging(self, comment_id: int) -> bool:
        post_author_id = self.database.get_information(
            self.comment_belonging_request.format(comment_id=comment_id), (0, ))[0]
        return post_author_id == self.user_id

    @property
    def get_posts(self) -> dict:
        return self.posts

    def __iter__(self):
        return self

    def __next__(self):
        if self.count >= len(self.posts):
            self.count = 0
            raise StopIteration
        else:
            self.count += 1
            return list(self.posts.values())[self.count - 1]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(user_id={self.user_id})"


class UserSubscriptionManager(UserManager):
    """Manager for controlling subscriptions"""
    subscribers_query = 'SELECT subscriber_id FROM subscriptions WHERE author_id={author_id}'
    subscribed_to_query = 'SELECT author_id FROM subscriptions WHERE subscriber_id={subscriber_id}'
    subscribe_request = 'INSERT OR IGNORE INTO subscriptions(subscriber_id, author_id, created_on) ' \
                        'VALUES (?, ?, ?)'
    unsubscribe_request = 'DELETE FROM subscriptions WHERE subscriber_id={subscriber_id} ' \
                          'AND author_id={author_id}'

    def __init__(self, user_id: int) -> None:
        super().__init__(user_id, 4)

    def subscribe(self, user_id: int) -> None:
        self.database.insert(self.subscribe_request, data=(self.user_id, user_id,
                                                           datetime.now().strftime('%Y-%m-%d')))

    def unsubscribe(self, user_id: int) -> None:
        self.database.delete(self.unsubscribe_request.format(subscriber_id=self.user_id,
                                                             author_id=user_id))

    @property
    def get_followers(self) -> list:
        return list(self.database.get_all_singles(self.subscribers_query.format(author_id=self.user_id)))

    @property
    def get_follows(self) -> tuple:
        return tuple(self.database.get_all_singles(self.subscribed_to_query.format(subscriber_id=self.user_id)))
