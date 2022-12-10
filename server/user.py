import datetime
import os
from enum import Enum
from abc import ABC, abstractmethod
from typing import Union, Optional
from ast import literal_eval

from flask_login import UserMixin
from flask_mail import Mail, Message

from server.managers import UserSubscriptionManager, UserPostManager
from server.posts import FullyFeaturedPost, Comment
from server.database import DataBase


class UserRole(Enum):
    AnonymousUser = -1
    EmailNotConfirmed = 0
    Viewer = 1
    Author = 2
    Admin = 3


class User(UserMixin, ABC):
    """Basic representation of a user.
    :param data: a tuple of 5 (id, login, email_address, registration_date, status)"""

    def __init__(self, data: tuple) -> None:
        self.user_id, self.login, self.email_address, self.register_date, self.status = data[:5]
        self.interests: dict = literal_eval(data[-1])
        self.SubscriptionManager = UserSubscriptionManager(self.user_id)
        self.avatar = self._get_avatar()

    def update_interests(self, interests: dict) -> None:
        DataBase(access_level=3).update(f'UPDATE users SET interests="{interests}" WHERE id={self.user_id}')
        self.interests = interests

    def view_post(self, post_id: int):
        query = 'UPDATE posts SET views=CASE WHEN EXISTS ' \
                '   (SELECT user_id FROM post_views WHERE user_id={user_id} AND post_id={post_id})' \
                '       THEN (SELECT views FROM posts WHERE post_id={post_id}) ' \
                '   ELSE ((SELECT views FROM posts WHERE post_id={post_id})+1) END WHERE post_id={post_id}; ' \
                'INSERT OR IGNORE INTO post_views(user_id, post_id, created_on) VALUES ({user_id}, {post_id}, "{time}")'
        DataBase(access_level=4).execute_script(query.format(user_id=self.user_id,
                                                             post_id=post_id, time=self._get_time()))

    def change_like_status(self, post_id: int, new_status: int = 1) -> None:
        if new_status == '1':
            query = 'INSERT INTO post_likes(user_id, post_id, created_on) VALUES (?, ?, ?)'
            DataBase(access_level=2).insert(query, data=(self.user_id, post_id, self._get_time()))
        elif new_status == '0':
            DataBase(access_level=4).delete(f'DELETE FROM post_likes '
                                            f'WHERE user_id={self.user_id} AND post_id={post_id}')

    @staticmethod
    def _get_time():
        return datetime.datetime.now().strftime('%Y-%m-%d')

    def check_if_liked(self, post_id):
        query = f'SELECT user_id FROM post_likes WHERE ' \
                f'user_id={self.user_id} AND post_id={post_id}'
        res = DataBase(access_level=1).get_information(query, default=(0, ))
        return res

    def _get_avatar(self) -> str:
        return '/' + path if os.path.exists((path := f'static/avatar_images/{self.user_id}.jpeg')) \
            else '/static/avatar_images/0.jpeg'

    @property
    def get_user_id(self) -> int:
        return self.user_id

    @property
    def get_login(self) -> str:
        return self.login

    @property
    def get_email(self) -> str:
        return self.email_address

    @property
    @abstractmethod
    def get_role(self):
        """Get a role of the user."""

    @property
    def get_avatar(self) -> str:
        return self.avatar

    @property
    def is_authenticated(self) -> bool:
        if self.status <= 0:
            return False
        else:
            return True

    @property
    def get_interests(self) -> dict:
        return self.interests

    def get_id(self) -> str:
        try:
            return str(self.user_id)
        except AttributeError:
            raise NotImplementedError("No `id` attribute - override `get_id`") from None

    def __repr__(self) -> str:
        parameters_string = ''
        for attr in self.__dict__.items():
            parameters_string += f"{attr[0]} = {attr[1]}, \n\t"

        return f'{self.__class__.__name__}({parameters_string})'


class Viewer(User):
    """User that hasn't made any posts."""

    def __init__(self, data: tuple) -> None:
        super().__init__(data)

    @property
    def get_role(self) -> UserRole.Viewer:
        return UserRole.Viewer


class Author(User):
    """User that uploaded at least once, and
    his article was verified by admins."""

    reply_sql = f'INSERT INTO comments(post_id, user_id, comment, date, is_reply, status) ' \
                f'VALUES(?, ?, ?, ?, ?, ?);'

    def __init__(self, data: tuple) -> None:
        super().__init__(data)
        self.PostManager = UserPostManager(self.user_id)

    def send_notification(self, post_id: int, app) -> None:
        """Send notification about the new publication made to all of user's
        subscribers."""
        mail = Mail(app)
        article = FullyFeaturedPost(post_id)
        tags_info = f' about {", ".join(tags)}' if (tags := article.get_tags(True)) else ''
        message = Message(f'{self.login} released new article.',
                          recipients=self._get_followers_emails())
        message.html = f'{self.login} released an article "{article.get_title}"{tags_info}'
        mail.send(message)

    def _get_followers_emails(self) -> list:
        """Get email of all user's subscribers."""
        followers_ids = tuple(fol) if len(fol := self.SubscriptionManager.get_followers) \
            != 1 else f'({fol[0]})'  # sqlite break if the expression `SELECT ... IN `
        # used with the tuple with a single element inside it (e.g. with the
        # tuple that looks something like this: `(1,)`), so it needs to be converted to a string
        # like `(1)`.
        emails = DataBase().get_all_singles(f'SELECT email FROM users WHERE id IN {followers_ids}')
        return emails

    def author_reply(self, post_id: int, reply_text: str,
                     accurate_time: str, comment_id: int) -> None:
        """Reply to a comment. This method should be specifically used when the
        author replies to a comment under his posts, because it gives the comment a
        status that indicates that the comment is helpful/interesting."""
        database = DataBase(access_level=3)
        data_package = (post_id, self.user_id, reply_text, accurate_time, comment_id, 1)
        database.insert(self.reply_sql, data=data_package)
        database.update(f'UPDATE comments SET status=2 WHERE comment_id="{comment_id}"')

    def author_ban_comment(self, current_app, comment_id: int, reason: Optional[str] = None) -> None:
        """Bun a comment under the user's post."""
        CommentBanMessageSender(current_app, comment_id,
                                self.get_login, reason).send_ban_notification()

    @property
    def get_role(self) -> UserRole.Author:
        """Get the role of the user."""
        return UserRole.Author


class Admin(User):
    """User with special rights to ban or verify posts."""

    def __init__(self, data: tuple) -> None:
        super().__init__(data)
        self.PostManager = UserPostManager(self.user_id)

    @classmethod
    def verify_post(cls, post_id: int, app) -> None:
        """Set the post's status to `verified`, make other users able to see it."""
        db = DataBase(access_level=3)
        db.update(f'UPDATE posts SET verified=1 WHERE post_id={post_id}')
        article_author = UserFactory.create_author(db.get_information(f'SELECT user_id FROM posts'
                                                                      f' WHERE post_id={post_id}')[0])
        article_author.send_notification(post_id, app)

    def ban_post(self, post_id: int, problem_description: str, current_app) -> None:
        """Ban a post, email the author to inform him that post was banned."""
        PostBanMessageSender(current_app, post_id, problem_description,
                             self.get_email).send_ban_notification()

    @property
    def get_role(self) -> UserRole.Admin:
        return UserRole.Admin


class EmailBanMessageSender(ABC):
    database = DataBase()

    def __init__(self, app):
        self.mail = Mail(app)

    def _get_user_data(self, user_id: int) -> tuple[str, str]:
        """Look for the user's email in database using given login."""
        return self.database.get_information(f'SELECT email, login FROM users WHERE id="{user_id}"')

    def _get_post_data(self, post_id: int) -> tuple:
        """Get post's title and the id of the author by its id."""
        return self.database.get_information(f'SELECT title, user_id FROM posts '
                                             f'WHERE post_id="{post_id}"')

    @abstractmethod
    def send_ban_notification(self) -> None:
        """General function for construction and sending an email message."""

    @abstractmethod
    def _update_status(self) -> None:
        """Set the object's status to 'banned'."""

    @abstractmethod
    def _build_message(self) -> Message:
        """Construct the email message."""


class CommentBanMessageSender(EmailBanMessageSender):
    standard_message = 'Dear {}, \n' \
                       'This message is sent to you by PronamkaScience to ' \
                       'inform you that one of your comments - "{}" ' \
                       'under the post "{}" of user {} ' \
                       'was banned{}. \n' \
                       'Post author has a right to ban any comments under their posts, ' \
                       'so, please, check out the policy of the author before writing comments.'

    def __init__(self, app, comment_id: int, author_login: str,
                 reason: Optional[str] = None) -> None:
        super().__init__(app)
        self.comment_id = comment_id
        self.comment = Comment(comment_id)
        self.post_title = self._get_post_data(self.comment.post_id)[0]
        self.post_author_login = author_login
        self.user_email, self.user_login = self._get_user_data(self.comment.user_id)
        self.reason = reason

    def send_ban_notification(self) -> None:
        """General function for construction and sending an email message."""
        self._update_status()
        self.mail.send(self._build_message())

    def _update_status(self) -> None:
        """Set comments status  to 2(banned)."""
        DataBase(access_level=3).update(f'UPDATE comments SET status=3 '
                                        f'WHERE comment_id="{self.comment_id}"')

    def _build_message(self) -> Message:
        """Construct the email message."""
        message = Message(f'Comment "{self.comment.text}" was banned.',
                          recipients=[self.user_email],
                          sender=('PronamkaScience', 'defender0508@gmail.com'))
        body = self.standard_message.format(self.user_login, self.comment.get_text,
                                            self.post_title, self.post_author_login,
                                            self._build_reason())
        message.html = body
        return message

    def _build_reason(self) -> str:
        if self.reason:
            return ' for the following reason: ' + self.reason
        else:
            return ''


class PostBanMessageSender(EmailBanMessageSender):
    standard_message = 'Dear {}, \n' \
                       'This message is sent to you by PronamkaScience to ' \
                       'inform you that one of your posts - "{}" ' \
                       'was banned for the following reason: "{}". \n' \
                       'If you have any questions or complains, please contact the ' \
                       'member of our post-checking crew on the platform or ' \
                       'at {}.'

    def __init__(self, app, post_id: int, problem_description: str,
                 admin_email: str):
        super().__init__(app)
        self.admin_email = admin_email
        self.problem_description = problem_description
        self.post_id = post_id
        self.post_title, user_id = self._get_post_data(post_id)
        self.user_email, self.post_author = self._get_user_data(user_id)

    def send_ban_notification(self) -> None:
        """General function for construction and sending an email message."""
        self._update_status()
        self.mail.send(self._build_message())

    def _update_status(self) -> None:
        """Set post status from 0(or from 1, but unlikely) to 2(banned)."""
        DataBase(access_level=3).update(f'UPDATE posts SET verified=2 '
                                        f'WHERE post_id="{self.post_id}"')

    def _build_message(self) -> Message:
        """Construct the email message."""
        message = Message(f'Post "{self.post_title}" was banned.', recipients=[self.user_email],
                          sender=('PronamkaScience', 'defender0508@gmail.com'))
        body = self.standard_message.format(self.post_author, self.post_title,
                                            self.problem_description, self.admin_email)
        message.html = body
        return message


class UserFactory:
    """Class for creating different user instances."""
    database = DataBase()

    @classmethod
    def create_auto(cls, user_id: int) -> Union[Viewer, Author, Admin]:
        """Automatically decides, which role user should
        have by looking it up in the database."""
        _actions = {UserRole.Viewer: cls.create_viewer,
                    UserRole.Author: cls.create_author,
                    UserRole.Admin: cls.create_admin}
        # noinspection PyArgumentList
        return _actions.get(cls.get_role(user_id))(user_id)

    @classmethod
    def get_role(cls, user_id: int) -> UserRole:
        return UserRole(int(cls.database.get_information(f'SELECT role FROM users WHERE id="{user_id}"')[0]))

    @classmethod
    def create_viewer(cls, user_id: int) -> Viewer:
        """Create a viewer instance.
        WARNING: if a user with given id does not exist, AssertionError will be raised"""
        data = cls._get_data(user_id)
        return Viewer(data)

    @classmethod
    def create_author(cls, user_id: int) -> Author:
        data = cls._get_data(user_id)
        return Author(data)

    @classmethod
    def create_admin(cls, user_id: int) -> Admin:
        data = cls._get_data(user_id)
        return Admin(data)

    @classmethod
    def _get_data(cls, user_id: int) -> tuple:
        data = cls.database.get_information(f"SELECT id, login, email, registration_date, status, interests "
                                            f"FROM users WHERE id='{user_id}'")
        assert data is not None, 'User with given id does not exist. If you encountered this error, ' \
                                 'please contact us at defender0508@gmeail.com'
        return data

    @classmethod
    def update_role(cls, user_id: int):
        """Update the Viewer instance to Author one.
        This method gets called when a user makes his first post."""
        DataBase(access_level=3).update(f'UPDATE users SET role="2" WHERE id="{user_id}"')
        data = cls._get_data(user_id)
        return Author(data)
