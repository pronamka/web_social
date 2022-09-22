from datetime import datetime
from time import sleep
from threading import Thread
from Lib.updates.managers import Manager


class UsersObserver(Manager):
    """Class for tracking users' conditions."""

    def __init__(self):
        super().__init__()

    def check_unconfirmed_users(self):
        """Delete all users, who did not confirm their email addresses in an hour.
        (So user can create a new account with his email.)"""
        while True:
            self._check_on_loop()
            sleep(3600)

    def _check_on_loop(self):
        current_time = datetime.now().strftime('%H:%M')
        for i in self._get_users():
            if self._manage_time(i[0]) < current_time:
                self.database.delete(f"DELETE FROM users WHERE id='{i[0]}'")

    def _get_users(self):
        users = self.database.get_all("SELECT id, registration_date FROM users WHERE is_activated='0'")
        return users

    @staticmethod
    def _manage_time(time: str) -> str:
        comparison_time = time.rsplit(' ', maxsplit=1)[1]
        if int(comparison_time.split(':')[0]) >= 23:
            comparison_time = '00' + ':' + comparison_time.split(':')[1]
        else:
            comparison_time = str(int(comparison_time.split(':')[0]) + 1) + ':' + comparison_time.split(':')[1]
        return comparison_time


