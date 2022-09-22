import sqlite3
from enum import Enum
from flask_login import UserMixin
from Lib.server.managers import SubscriptionManager, UserPosts
from Lib.server.database import DataBase


class UserAccountState(Enum):
    AnonymousUser = -1
    EmailNotConfirmed = 0
    NormalUser = 1
    AdminUser = 2
    UserNotFound = 3


class User(UserMixin, SubscriptionManager, UserPosts):
    """User object with its properties"""
    def __init__(self, login: str) -> None:
        self.login = login
        self.database = DataBase()
        user_info = self._get_user_info()
        self.id = user_info[0]
        self.email_address = user_info[1]
        self.register_date = user_info[2]
        self.status: UserAccountState = UserAccountState(user_info[3])
        super().__init__(self.id)

    def _get_user_info(self) -> tuple:
        try:
            information = self.database.get_information(f"""SELECT id, email, registration_date, is_activated, role 
                                FROM users WHERE login='{self.login}'""")
            return information
        except sqlite3.Error:
            self.status = UserAccountState(4)

    def define_properties(self, info):  # in development
        self.id = info[0]
        self.email_address = info[1]
        self.register_date = info[2]
        self.status = UserAccountState(info[3])

    def get(self):
        if self.status != 2 and self.status != 3:
            return None
        else:
            return str(self.id)

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False
