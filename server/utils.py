from datetime import datetime
from time import sleep
from docx2pdf import convert
from pythoncom import CoInitializeEx
import os
from typing import Union

from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from PIL import Image
from pdfkit import from_file, configuration

from server.database import DataBase
from server.search_engine import check_integrity, get_text

allowed_extensions = ('txt', 'jpg', 'docx', 'jpeg', 'png', 'pdf', 'xlsx', 'jpeg', 'html')


class ExtensionNotAllowed(PermissionError):

    def __init__(self, filename: str) -> None:
        self.message = f'File with filename {filename} has an unexpected file extension.'

    def __repr__(self) -> str:
        return self.message


class SymbolsNotAllowed(OSError):

    def __init__(self, filename: str, symbol: str) -> None:
        self.message = f'File with filename {filename} has unexpected symbols in it.' \
                       f'Symbol that caused this error: {symbol}'

    def __repr__(self) -> str:
        return self.message


class FileManager:
    """Class for converting/saving docx/pdf files.
    :param file: FileStorage: a docx/pdf file received from js request.
    :param user_id: an int - id of a post's author"""

    upload_path = 'static/upload_folder/'
    wkhtmltopdf_config = configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
    wkhtmltopdf_options = {'enable-local-file-access': True}

    def __init__(self, file: FileStorage, user_id: int) -> None:
        self.errors = []
        self.file = file  # the file is of type FileStorage, not ImmutableMultiDict
        self.user_id = user_id
        self.filename = self._security_check()
        self.full_path = None
        self.protocols = {'pdf': self._immediate_save, 'docx': self._save_from,
                          'html': self._save_from}

    def save(self) -> Union[str, None]:
        """General function for saving files(and converting them into
        pdf if necessary). Also checks file integrity and uniqueness of
        its name.
        :returns: str, if an error occurred; None if file was successfully
        saved and an entry made in database."""
        if conditions := self._check_conditions():
            return conditions
        self.full_path = os.path.join(self.upload_path, self.filename)
        self.protocols.get(self._get_extension())()
        if error := self._insert_into_db():
            return error

    def _insert_into_db(self) -> None:
        """Creates an entry in the database with the
        information about new post."""
        date = datetime.now()
        data_package = (self.user_id, self._new_filename(False), date.strftime('%Y-%m-%d'),
                        date.strftime("%A, %d. %B %Y %H:%M"), get_text(self._new_filename()))
        DataBase(access_level=2).insert(f'INSERT INTO posts(user_id, title, date, display_date, '
                                        f'raw_text) VALUES(?, ?, ?, ?, ?);', data=data_package)

    def _check_conditions(self) -> Union[str, None]:
        """Check if there is anything wrong with
        file's name, and it's integrity.
        :returns: str, if there is an error(note that it
                  will only return a message about the latest
                  error occurred); None, if no errors occurred."""
        if self.errors:
            return self.errors.pop().__repr__()
        if DataBase().get_information(f'SELECT title FROM posts WHERE title="{self._new_filename(False)}"'):
            return 'A post with this name already exists, so your file was not saved.' \
                   'Please give it a different name.'

    def _get_extension(self) -> str:
        """Get the extension of the file given.
        :returns: str with the file extension (without '.')"""
        return self.filename.rsplit('.', 1)[1]

    def _immediate_save(self) -> str:
        """Just save a file (called when the file already has the right extension)."""
        if self._get_extension() == 'pdf' and check_integrity(self.file.stream) is False:
            #  self.file.stream is of type SpooledTemporaryFile
            return 'Sorry, we were unable to save your file. ' \
                   'This is likely because it was corrupted. ' \
                   'If it opens fine on your device, please contact ' \
                   'our tech support at defender0508@gmail.com'
        self.file.save(self.full_path)

    def _save_from(self):
        _actions = {'docx': self._convert_from_docx, 'html': self._convert_from_html}
        self.file.save(self.full_path)
        _actions.get(self._get_extension())()
        os.remove(self.full_path)

    def _convert_from_html(self):
        """Convert file from html to pdf and save it on disk."""
        from_file(self.full_path, self._new_filename(),
                  options=self.wkhtmltopdf_options, configuration=self.wkhtmltopdf_config)

    def _convert_from_docx(self) -> None:
        """Convert file from docx to pdf and save it on disk."""
        CoInitializeEx(0)
        convert(self.full_path, self._new_filename())

    def _security_check(self) -> Union[str, None]:
        """Check if the file has allowed extension and
        only numbers and english letters in its name.
        :returns: str, if the filename is fine; None, if
        there is something wrong with it. (that way an
        error will be appended to the error log.)"""
        filename = self.file.filename
        chars = list(map(ord, filename))
        for i in chars:
            if not (45 <= i <= 57 or 65 <= i <= 122):
                self.errors.append(SymbolsNotAllowed(filename, chr(i)))
        if filename.rsplit('.', 1)[1] in ('docx', 'pdf', 'html'):
            return secure_filename(filename)
        else:
            self.errors.append(ExtensionNotAllowed(filename))

    def _new_filename(self, full: bool = True) -> str:
        if not full:
            name = self.filename
        else:
            name = self.full_path
        return name.split('.', maxsplit=1)[0]+'.pdf'


def convert_image(name: str) -> None:
    """Convert an image from png or jpg to jpeg
    Saves all files in ../static/avatar_images/"""
    if name.rsplit('.', maxsplit=1)[1] != 'jpeg':  # check if picture already in jpeg format
        path = f'../static/avatar_images/{name}'  # construct path
        image = Image.open(path)  # create an image object
        jpeg = image.convert('RGB')  # convert image into RGB representation
        os.remove(f'../static/avatar_images/{name}')  # delete the old image
        jpeg.save(f'../static/avatar_images/{name.split(".")[0]}.jpeg')  # save the representation as jpeg


class UsersObserver:
    """Class for tracking users' conditions."""

    database = DataBase(access_level=4)

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

    @classmethod
    def _get_users(cls):
        users = cls.database.get_all("SELECT id, registration_date FROM users WHERE status='0'")
        return users

    @staticmethod
    def _manage_time(time: str) -> str:
        comparison_time = time.rsplit(' ', maxsplit=1)[1]
        if int(comparison_time.split(':')[0]) >= 23:
            comparison_time = '00' + ':' + comparison_time.split(':')[1]
        else:
            comparison_time = str(int(comparison_time.split(':')[0]) + 1) + ':' + comparison_time.split(':')[1]
        return comparison_time
