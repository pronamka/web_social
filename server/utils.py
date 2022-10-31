from datetime import datetime
from time import sleep
import pythoncom
import os

from werkzeug.utils import secure_filename
from PIL import Image
from docx2pdf import convert as convert_to_pdf

from server.managers import Manager
from server.database import DataBase

allowed_extensions = ('txt', 'jpg', 'docx', 'jpeg', 'png', 'pdf', 'xlsx', 'jpeg')


class ExtensionNotAllowed(PermissionError):
    __slots__ = 'message'

    def __init__(self, filename: str) -> None:
        self.message = f'File with filename {filename} has an unexpected file extension.'

    def __repr__(self) -> str:
        return self.message


class SymbolsNotAllowed(OSError):
    __slots__ = 'message'

    def __init__(self, filename: str, symbol: str) -> None:
        self.message = f'File with filename {filename} has unexpected symbols in it.' \
                       f'Symbol that caused this error: {symbol}'

    def __repr__(self) -> str:
        return self.message


class FileManager:
    __slots__ = 'file', 'user_id', 'filename', 'protocols'
    upload_path = 'static/upload_folder/'

    def __init__(self, file, user_id: int) -> None:
        self.file = file
        self.user_id = user_id
        self.filename = self.security_check()
        self.protocols = {'pdf': self.immediate_save, 'docx': self.save_as_pdf}

    def save(self):
        date = datetime.now()
        DataBase(access_level=2).create(f'INSERT INTO posts(user_id, title, date, display_date) '
                                        f'VALUES(?, ?, ?, ?);',
                                        data=(self.user_id,
                                              self.filename,
                                              date.strftime('%Y-%m-%d'),
                                              date.strftime("%A, %d. %B %Y %H:%M")))
        # noinspection PyArgumentList
        self.protocols.get(self.get_extension())(self.file)

    def get_extension(self) -> str:
        return self.filename.rsplit('.', 1)[1]

    def immediate_save(self, file):
        file.save(os.path.join(self.upload_path, self.filename))

    def save_as_pdf(self, file):
        file.save(os.path.join(self.upload_path, self.filename))
        self._convert_and_save()
        os.remove(f'static/upload_folder/{self.filename}')

    def _convert_and_save(self):
        pythoncom.CoInitializeEx(0)
        convert_to_pdf(os.path.join(self.upload_path, self.filename),
                       os.path.join(self.upload_path, str(self.filename.rsplit('.', 1)[0] + '.pdf')))

    def security_check(self) -> str:
        filename = self.file.filename
        chars = list(map(ord, filename))
        for i in chars:
            if not(45 <= i <= 57 or 65 <= i <= 122):
                raise SymbolsNotAllowed(filename, chr(i))
        if filename.rsplit('.', 1)[1] == 'docx':
            return secure_filename(filename)
        else:
            raise ExtensionNotAllowed


def convert_image(name: str) -> None:
    """Convert an image from png or jpg to jpeg
    Saves all files in ../static/avatar_images/"""
    if name.rsplit('.', maxsplit=1)[1] != 'jpeg':  # check if picture already in jpeg format
        path = f'../static/avatar_images/{name}'  # construct path
        image = Image.open(path)  # create an image object
        jpeg = image.convert('RGB')  # convert image into RGB representation
        os.remove(f'../static/avatar_images/{name}')  # delete the old image
        jpeg.save(f'../static/avatar_images/{name.split(".")[0]}.jpeg')  # save the the representation as jpeg


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
            if self._manage_time(i[1]) < current_time:
                self.database.delete(f"DELETE FROM users WHERE id='{i[0]}'")

    def _get_users(self):
        users = self.database.get_all("SELECT id, registration_date FROM users WHERE status='0'")
        return users

    @staticmethod
    def _manage_time(time: str) -> str:
        comparison_time = time.rsplit(' ', maxsplit=1)[1]
        if int(comparison_time.split(':')[0]) >= 23:
            comparison_time = '00' + ':' + comparison_time.split(':')[1]
        else:
            comparison_time = str(int(comparison_time.split(':')[0]) + 1) + ':' + comparison_time.split(':')[1]
        return comparison_time
