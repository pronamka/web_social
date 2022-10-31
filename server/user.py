from enum import Enum
from abc import ABC
from flask_login import UserMixin
from os.path import exists
from server.managers import UserSubscriptionManager, UserPostManager
from server.database import DataBase


class UserRole(Enum):
    AnonymousUser = -1
    EmailNotConfirmed = 0
    Viewer = 1
    Creator = 2
    Admin = 3


class User1(UserMixin, UserSubscriptionManager, UserPostManager):
    """User object with its properties"""
    def __init__(self, user_id: int) -> None:
        self.id = user_id
        super().__init__(self.id)
        user_info = self._get_user_info()
        self.login, self.email_address, self.register_date, self.status = user_info[0:2]
        self.role = UserRole(user_info[3])

    def _get_user_info(self) -> tuple:
        information = self.database.get_information(f"""SELECT login, email, registration_date, status, role 
                            FROM users WHERE login='{self.login}'""")
        return information

    def define_properties(self, info):  # in development
        self.id = info[0]
        self.email_address = info[1]
        self.register_date = info[2]
        self.status = UserRole(info[3])

    def get(self):
        if self.status != 2 and self.status != 3:
            return None
        else:
            return str(self.id)

    @property
    def get_role(self):
        return self.role.value

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        if self.status == -1 or self.status == 0:
            return False
        else:
            return True

    @property
    def is_anonymous(self):
        return False


class User(UserMixin, ABC):
    """Basic representation of a user.
    :param list data: a list of 6 values"""
    database = DataBase()

    def __init__(self, data: list) -> None:
        self.user_id, self.login, self.email_address, self.register_date, self.status, self.role = data
        self.SubscriptionManager = UserSubscriptionManager(self.user_id)
        self.avatar = self._get_avatar()

    def _get_avatar(self):
        return f'{self.user_id}.jpeg' if exists(f'static/avatar_images/{self.user_id}.jpeg') else '0.jpeg'

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
    def get_role(self):
        return self.role

    @property
    def get_avatar(self):
        return f'static/avatar_images/{self.avatar}'

    @property
    def is_authenticated(self):
        if self.status == -1 or self.status == 0:
            return False
        else:
            return True

    def __repr__(self):
        parameters_string = ''
        for attr in self.__dict__.items():
            parameters_string += f"{attr[0]} = {attr[1]}, \n\t"

        return f'{self.__class__.__name__}({parameters_string})'


class Viewer(User):
    def __init__(self, data: list) -> None:
        super().__init__(data)


class Author(User):
    def __init__(self, data):
        super().__init__(data)
        self.PostManager = UserPostManager(self.user_id)


class Admin(User):
    def __init__(self, data):
        super().__init__(data)
        self.PostManager = UserPostManager(self.user_id)


class UserFactory:
    database = DataBase()

    @classmethod
    def create_viewer(cls, user_id: int) -> Viewer:
        """Create a viewer instance.
        WARNING: if a user with given id does not exist, AssertionError will be raised"""
        data = cls._get_data(user_id)
        data.insert(5, UserRole(1))
        return Viewer(data)

    @classmethod
    def create_author(cls, user_id: int) -> Author:
        data = cls._get_data(user_id)
        data.insert(5, UserRole(2))
        return Author(data)

    @classmethod
    def create_admin(cls, user_id: int) -> Admin:
        data = cls._get_data(user_id)
        data.insert(5, UserRole(3))
        return Admin(data)

    @classmethod
    def _get_data(cls, user_id: int) -> list:
        data = cls.database.get_information(f"SELECT login, email, registration_date, status "
                                            f"FROM users WHERE id='{user_id}'")
        assert data is not None, 'User with given id does not exist. If you encountered this error, ' \
                                 'please contact us at defender0508@gmeail.com'
        data = [i for i in data]
        data.insert(0, user_id)
        return data

    @classmethod
    def create_and_update(cls, user_id: int):
        DataBase(access_level=3).update(f'UPDATE users SET role="2" WHERE id="{user_id}"')
        data = cls._get_data(user_id)
        data.insert(5, UserRole(2))
        return Author(data)

