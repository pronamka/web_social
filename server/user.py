import os
from enum import Enum
from abc import ABC, abstractmethod
from typing import Union

from flask_login import UserMixin
from flask_mail import Mail, Message

from server.search_engine import add_article_to_search
from server.managers import UserSubscriptionManager, UserPostManager
from server.database import DataBase


class UserRole(Enum):
    AnonymousUser = -1
    EmailNotConfirmed = 0
    Viewer = 1
    Creator = 2
    Admin = 3


class User(UserMixin, ABC):
    """Basic representation of a user.
    :param data: a tuple of 5 (id, login, email_address, registration_date, status)"""

    def __init__(self, data: tuple) -> None:
        self.user_id, self.login, self.email_address, self.register_date, self.status = data
        self.SubscriptionManager = UserSubscriptionManager(self.user_id)
        self.avatar = self._get_avatar()

    def _get_avatar(self):
        return path if os.path.exists((path := f'static/avatar_images/{self.user_id}.jpeg')) \
            else 'static/avatar_images/0.jpeg'

    @property
    def get_user_id(self):
        return self.user_id

    @property
    def get_login(self):
        return self.login

    @property
    def get_email(self):
        return self.email_address

    @property
    @abstractmethod
    def get_role(self):
        """Get a role of the user."""

    @property
    def get_avatar(self):
        return self.avatar

    @property
    def is_authenticated(self):
        if self.status <= 0:
            return False
        else:
            return True

    def get_id(self):
        try:
            return str(self.user_id)
        except AttributeError:
            raise NotImplementedError("No `id` attribute - override `get_id`") from None

    def __repr__(self):
        parameters_string = ''
        for attr in self.__dict__.items():
            parameters_string += f"{attr[0]} = {attr[1]}, \n\t"

        return f'{self.__class__.__name__}({parameters_string})'


class Viewer(User):
    def __init__(self, data: tuple) -> None:
        super().__init__(data)

    @property
    def get_role(self):
        return UserRole.Viewer


class Author(User):
    def __init__(self, data: tuple):
        super().__init__(data)
        self.PostManager = UserPostManager(self.user_id)

    @property
    def get_role(self):
        return UserRole.Creator


class Admin(User):
    def __init__(self, data: tuple):
        super().__init__(data)
        self.PostManager = UserPostManager(self.user_id)

    @staticmethod
    def verify_post(post_id: int, post_title: str) -> None:
        DataBase(access_level=3).update(f'UPDATE posts SET verified=1 WHERE post_id="{post_id}"')
        add_article_to_search(post_title, post_id)

    def ban_post(self, post_id, problem_description, current_app):
        EmailBanMessageSender(post_id, problem_description, self.get_email, current_app).send_ban_notification()
        # remove_article_from_search(post_id)

        # There is no need to remove article in most cases, as they are
        # only added to search when verified, so if they get banned, it
        # often means they were not verified before.
        # Special method will be implemented to ban posts that were
        # verified. (in cases there is something wrong with
        # copyrighting etc.)

    @property
    def get_role(self):
        return UserRole.Admin


class EmailBanMessageSender:
    """Class for sending notifications about banning
    user's post. It is not a subclass of EmailSenderWithToken,
    as it doesn't require one."""
    database = DataBase()
    standard_message = 'Dear {}, \n' \
                       'This message is sent to you by PronScience to ' \
                       'inform you that one of your posts - "{}" ' \
                       'was banned for the following reason: "{}". \n' \
                       'If you have any questions or complains, please contact the ' \
                       'member of our post-checking crew on the platform or ' \
                       'at {}.'

    def __init__(self, post_id: int, problem_description: str,
                 admin_email: str, current_app) -> None:
        self.admin_email = admin_email
        self.problem_description = problem_description
        self.post_id = post_id
        self.post_title, user_id = self._get_post_data(post_id)
        self.user_email, self.post_author = self._get_user_data(user_id)
        self.mail = Mail(current_app)

    def _get_post_data(self, post_id: int) -> tuple:
        """Get post's title and the id of the author by its id."""
        return self.database.get_information(f'SELECT title, user_id FROM posts '
                                             f'WHERE post_id="{post_id}"')

    def send_ban_notification(self) -> None:
        """General function for construction and sending an email message."""
        self._update_post_status()
        self.mail.send(self._build_message())

    def _update_post_status(self) -> None:
        """Set post status from 0(or from 1, but unlikely) to 2(banned)."""
        DataBase(access_level=3).update(f'UPDATE posts SET '
                                        f'verified=2 WHERE post_id="{self.post_id}"')

    def _build_message(self) -> Message:
        """Construct the email message."""
        message = Message(f'Post "{self.post_title}" was banned.',
                          recipients=[self.user_email],
                          sender=('PronamkaScience', 'defender0508@gmail.com'))
        body = self.standard_message.format(self.post_author, self.post_title,
                                            self.problem_description, self.admin_email)
        message.html = body
        return message

    def _get_user_data(self, user_id: int) -> tuple[str, str]:
        """Look for the user's email in database using
        given login."""
        return self.database.get_information(f'SELECT email, login FROM users WHERE id="{user_id}"')


class UserFactory:
    """Class for creating different user instances."""
    database = DataBase()

    @classmethod
    def create_auto(cls, user_id: int) -> Union[Viewer, Author, Admin]:
        """Automatically decides, which role user should
        have by looking it up in the database."""
        _actions = {UserRole.Viewer: cls.create_viewer,
                    UserRole.Creator: cls.create_author,
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
        data = cls.database.get_information(f"SELECT id, login, email, registration_date, status "
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
