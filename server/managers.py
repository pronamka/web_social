from datetime import datetime
from ast import literal_eval
from abc import ABC
from typing import Optional, Literal

from server.database import DataBase
from server.posts import Post, UserPostRegistry, FullyFeaturedPost, Comment, CommentsRegistry


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
        self.database.insert(query)

    def delete_post(self, post_id: int) -> None:
        self.database.delete(f"""DELETE FROM posts WHERE post_id='{post_id}'""")


class UserPostManager(UserManager):
    """Registry containing all post of a specific user"""
    # it's now made so this class has too many
    # responsibilities: both over posts and comments.
    # An effective way of separating them without
    # violating DRY should be found

    def __init__(self, user_id: int, *args) -> None:
        super(UserPostManager, self).__init__(user_id, 4)
        self.posts = {}
        self.post_ids = []
        self.comments = {}
        self.post_manger = PostManager(4)
        self.count = 0
        self.post_amount = 0
        self.comments_amount = 0

    """def fetch_posts(self, amount: int) -> int:
        for post in UserPostRegistry.get_posts(amount, len(self.posts),
                                               {'of_user': self.user_id}, FullyFeaturedPost):
            self.post_ids.append(post.get_id)
            self.posts[self.post_amount] = post
            self.post_amount += 1
        return self.post_amount

    def fetch_comments(self, amount):
        def get_comment_ids(comments_required):
            ids = tuple(self.post_ids) if len(self.post_ids) != 1 else '('+str(self.post_ids[0])+')'
            formatted_req = self.comments_request.format(ids, comments_required, self.comments_amount)
            comments = self.database.get_many_singles(formatted_req, size=comments_required)
            if len(comments) < comments_required:
                st_length = self.post_amount
                self.fetch_posts(2)
                if self.post_amount - st_length != 0:
                    comments += get_comment_ids(comments_required - len(comments))
            return comments

        for i in get_comment_ids(amount):
            self.comments[self.comments_amount] = Comment(i)
            self.comments_amount += 1
        return self.comments_amount"""

    def get_latest_posts(self, amount: int, start_with: int):
        res = UserPostRegistry.get_posts(amount, start_with, {'of_user': self.user_id})
        return res

    def get_latest_comments(self, amount: int, start_with: int):
        return CommentsRegistry.fetch_comments_on_users_post(amount, start_with, self.user_id)

    def get_post_amount(self):
        posts = self.database.get_information(f'SELECT COUNT(DISTINCT post_id) FROM posts '
                                              f'WHERE user_id="{self.user_id}"')
        return posts

    def get_comments_amount(self, post_id: int) -> tuple:
        comments = self.database.get_information(f'SELECT COUNT(DISTINCT comment_id) FROM comments '
                                                 f'WHERE post_id="{post_id}"')
        return comments

    def get_post(self, post_id: int) -> Post:
        assert self.posts.get(post_id) is not None, \
            f"No post with given id belongs to user: user id: {self.user_id}, requested post id: {post_id}"
        return self.posts.get(post_id)

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

    def __repr__(self):
        return f"{self.__class__.__name__}(user_id={self.user_id})"


class UserSubscriptionManager(UserManager):
    """Manager for controlling subscriptions"""

    def __init__(self, user_id: int) -> None:
        super().__init__(user_id, 3)
        self.followers, self.follows = list(map(literal_eval, self._get_followers()))

    def _get_followers(self):
        return self.database.get_information(f"SELECT followers, follows FROM users WHERE id='{self.user_id}'")

    def follow(self, user_id: int) -> None:
        self.check_if_subscribed(user_id)
        self.follows.append(user_id)
        UserSubscriptionManager(user_id).add_follower(self.user_id)
        self.database.update(f"UPDATE users SET follows='{self.follows}' WHERE id='{self.user_id}'")

    def add_follower(self, user_id: int) -> None:
        assert user_id not in self.followers, "Some user tried to follow you twice. " \
                                              "If you encountered this error, please contact " \
                                              "us at defender0508@gmeail.com"
        self.followers.append(user_id)
        self.database.update(f"UPDATE users SET followers='{self.followers}' WHERE id='{self.user_id}'")

    def unfollow(self, user_id: int) -> None:
        self.follows.remove(user_id)
        UserSubscriptionManager(user_id).remove_follower(self.user_id)
        self.database.update(f"UPDATE users SET follows='{self.follows}' WHERE id='{self.user_id}'")

    def remove_follower(self, user_id: int) -> None:
        self.followers.remove(user_id)
        self.database.update(f"UPDATE users SET followers='{self.followers}' WHERE id='{self.user_id}'")

    def find_by_id(self, user_id: int) -> str:
        return self.database.get_information(f"SELECT login FROM users WHERE id='{user_id}'")[0]

    def check_if_subscribed(self, user_id: int) -> None:
        assert user_id not in self.follows, "You tried to follow the person you are already following." \
                                            "If you encountered this error, " \
                                            "please contact us at defender0508@gmeail.com"

    @property
    def get_followers(self):
        return self.followers

    @property
    def get_follows(self) -> tuple:
        return tuple(self.follows)
