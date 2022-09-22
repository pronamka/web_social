from ast import literal_eval
from datetime import datetime
from Lib.server.database import DataBase
from Lib.server.post import Post


class Manager:
    """Basic manager object for any purposes"""
    def __init__(self):
        """Creates a database object"""
        self.database = DataBase()


class UserManger(Manager):
    """Manager for working with user properties"""
    def __init__(self, user_id: int) -> None:
        super().__init__()
        self.user_id = user_id


class PostManager(Manager):
    """Manager for creating or deleting posts"""
    def create_post(self, user_id: int, post_title: str) -> None:
        query = "INSERT INTO posts (user_id, title, date) VALUES (?, ?, ?);"
        data_package = (user_id, post_title, datetime.now().strftime("%A, %d. %B %Y %I:%M%p"))
        self.database.create(query, data=data_package)

    def delete_post(self, post_id: int) -> None:
        self.database.delete(f"""DELETE FROM posts WHERE post_id='{post_id}'""")


class UserPosts(UserManger):
    """Registry containing all post of a specific user"""
    def __init__(self, user_id: int) -> None:
        super(UserPosts, self).__init__(user_id)
        self.posts = self.get_all_posts()
        self.post_manger = PostManager()
        self.count = 0

    def get_all_posts(self) -> dict:
        all_posts = self.database.get_all(f"""SELECT post_id FROM posts WHERE user_id='{self.user_id}'""")
        all_posts = [item[0] for item in all_posts]
        return {item: Post(item) for item in all_posts}

    def delete_post(self, post_id: int) -> None:
        assert self.posts.get(post_id) is not None, \
            f"No post with given id belongs to user: user id: {self.user_id}, requested post id: {post_id}"
        self.post_manger.delete_post(post_id)
        self.posts.pop(post_id)

    def get_post(self, post_id: int) -> Post:
        assert self.posts.get(post_id) is not None, \
            f"No post with given id belongs to user: user id: {self.user_id}, requested post id: {post_id}"
        return self.posts.get(post_id)

    def create_post(self, post_title: str) -> None:
        self.post_manger.create_post(self.user_id, post_title)

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
            return list(self.posts.values())[self.count-1]

    def __repr__(self):
        return f"{self.__class__.__name__}(user_id: {self.user_id})"


class SubscriptionManager(UserManger):
    """Manager for controlling subscriptions"""
    def __init__(self, user_id: int) -> None:
        super().__init__(user_id)
        info = self._get_followers()  # needed because the function output contains tuple of strings, not lists
        self.followers = literal_eval(info[0])
        self.follows = literal_eval(info[1])

    def _get_followers(self):
        return self.database.get_information(f"SELECT followers, follows FROM users WHERE id='{self.user_id}'")

    def follow(self, user_id: int) -> None:
        self.check_if_subscribed(user_id)
        self.follows.append(user_id)
        SubscriptionManager(user_id).add_follower(self.user_id)
        self.database.update(f"UPDATE users SET follows='{self.follows}' WHERE id='{self.user_id}'")

    def add_follower(self, user_id: int) -> None:
        assert user_id not in self.followers, "Some user tried to follow you twice. " \
                                        "If you encountered this error, please contact us at defender0508@gmeail.com"
        self.followers.append(user_id)
        self.database.update(f"UPDATE users SET followers='{self.followers}' WHERE id='{self.user_id}'")

    def unfollow(self, user_id: int) -> None:
        self.follows.remove(user_id)
        SubscriptionManager(user_id).remove_follower(self.user_id)
        self.database.update(f"UPDATE users SET follows='{self.follows}' WHERE id='{self.user_id}'")

    def remove_follower(self, user_id: int) -> None:
        self.followers.remove(user_id)
        self.database.update(f"UPDATE users SET followers='{self.followers}' WHERE id='{self.user_id}'")

    def find_by_id(self, user_id: int) -> str:
        return self.database.get_information(f"SELECT login FROM users WHERE id='{user_id}'")[0]

    def check_if_subscribed(self, user_id: int) -> None:
        assert user_id not in self.follows, "You tried to follow the person you are already following." \
                                        "If you encountered this error, please contact us at defender0508@gmeail.com"

    @property
    def get_all_followers(self):
        return self.followers
