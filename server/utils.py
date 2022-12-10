from datetime import datetime, timedelta
from time import sleep
from docx2pdf import convert
from pythoncom import CoInitializeEx
import os
from typing import Union
from abc import ABC, abstractmethod
from io import BytesIO

from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from PIL import Image
from pdfkit import from_file, configuration

from PyPDF2 import PdfFileReader, errors, PdfReader
from server.database import DataBase

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


def check_integrity(stream) -> bool:
    """Check if it is possible to read the file.
    If it is not, PdfReader will raise PdfReadError while initializing.
    :param stream: an instance of tempfile.SpooledTemporaryFile
    :returns: True, if the file was read successfully;
              False, if an error occurred while reading (file is corrupted)"""
    try:
        PdfReader(stream)
        return True
    except errors.PdfReadError:
        return False


def get_text(name: str) -> str:
    """Get text from a pdf file saved on disk."""
    print(name)
    doc = PdfFileReader(name)
    text = ''
    for i in doc.pages:
        try:
            text += i.extract_text()
        except TypeError as e:
            print(f'An error occurred: {e}; The piece of text will be excluded from search.')
    return text


class FileManager(ABC):
    """ABC for any class that works with files received from client."""

    def __init__(self, file: FileStorage, user_id: int) -> None:
        self.errors = []
        self.file = file  # the file is of type FileStorage, not ImmutableMultiDict
        self.user_id = user_id
        self.filename = self._security_check()

    @abstractmethod
    def _get_allowed_extensions(self) -> tuple:
        """Return a tuple of strings representing extensions allowed for
        the file"""

    @abstractmethod
    def save(self):
        """General function for saving files(and converting them into
        pdf if necessary). Also checks file integrity and uniqueness of
        its name.
        :returns: str, if an error occurred; None if file was successfully
        saved and an entry made in database."""

    def _get_extension(self) -> str:
        """Get the extension of the file given.
        :returns: str with the file extension (without '.')"""
        return self.filename.rsplit('.', 1)[1]

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
        if filename.rsplit('.', 1)[1] in self._get_allowed_extensions():
            return secure_filename(filename)
        else:
            self.errors.append(ExtensionNotAllowed(filename))


class ArticleManager(FileManager):
    """Class for converting/saving docx/pdf files.
    :param file: FileStorage: a docx/pdf file received from js request.
    :param user_id: an int - id of a post's author"""

    insert_article_request = 'INSERT INTO posts(user_id, title, date, display_date, ' \
                             'tags, raw_text) VALUES(?, ?, ?, ?, ?, ?);'
    upload_path = 'static/upload_folder/'
    wkhtmltopdf_config = configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
    wkhtmltopdf_options = {'enable-local-file-access': True}

    def __init__(self, file: FileStorage, user_id: int, tags) -> None:
        super(ArticleManager, self).__init__(file, user_id)
        self.full_path = None
        self.tags = tags
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
        DataBase(access_level=2).insert(self.insert_article_request, data=self._build_data_package())

    def _build_data_package(self) -> tuple:
        """Prepare data that will be inserted in the database."""
        date = datetime.now()
        data_package = (self.user_id, self._new_filename(False), date.strftime('%Y-%m-%d'),
                        date.strftime("%A, %d. %B %Y %H:%M"), self.tags, get_text(self._new_filename()))
        return data_package

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

    def _immediate_save(self) -> Union[str, None]:
        """Just save a file (called when the file already has the right extension)."""
        if self._get_extension() == 'pdf' and check_integrity(self.file.stream) is False:
            #  self.file.stream is of type SpooledTemporaryFile
            return 'Sorry, we were unable to save your file. ' \
                   'This is likely because it was corrupted. ' \
                   'If it opens fine on your device, please contact ' \
                   'our tech support at defender0508@gmail.com'
        self.file.save(self.full_path)

    def _save_from(self) -> None:
        _actions = {'docx': self._convert_from_docx, 'html': self._convert_from_html}
        self.file.save(self.full_path)
        _actions.get(self._get_extension())()
        os.remove(self.full_path)

    def _convert_from_html(self) -> None:
        """Convert file from html to pdf and save it on disk."""
        from_file(self.full_path, self._new_filename(),
                  options=self.wkhtmltopdf_options, configuration=self.wkhtmltopdf_config)

    def _convert_from_docx(self) -> None:
        """Convert file from docx to pdf and save it on disk."""
        CoInitializeEx(0)
        convert(self.full_path, self._new_filename())

    def _get_allowed_extensions(self) -> tuple:
        return 'docx', 'pdf', 'html'

    def _new_filename(self, full: bool = True) -> str:
        if not full:
            name = self.filename
        else:
            name = self.full_path
        return name.split('.', maxsplit=1)[0]+'.pdf'


class ImageManager(FileManager):
    """Class for converting images to jpeg and
    saving them with the right name."""
    def __init__(self, file: FileStorage, user_id: int) -> None:
        super(ImageManager, self).__init__(file, user_id)

    def _get_allowed_extensions(self) -> tuple:
        return 'jpeg', 'jpg', 'png'

    def save(self) -> None:
        """Convert an image from png or jpg to jpeg
        Saves all files in ../static/avatar_images/"""
        if self._get_extension() != 'jpeg':  # check if picture already in jpeg format
            image = Image.open(BytesIO(self.file.read()))  # create an image object;
            # BytesIO passed to Image.open() allows to open to the image without first
            # saving it on the disk
            jpeg = image.convert('RGB')  # convert image into RGB representation
            jpeg.save(f'static/avatar_images/{self.user_id}.jpeg')  # save the representation as jpeg


class UsersObserver:
    """Class for tracking users' conditions."""

    database = DataBase(access_level=4)

    def check_unconfirmed_users(self) -> None:
        """Delete all users, who did not confirm their email addresses in an hour.
        (So user can create a new account with his email). It will stay active forever
        once launched."""
        while True:
            self._check_on_loop()
            sleep(3600)

    def _check_on_loop(self) -> None:
        """Check if the user hasn't confirmed his email in an hour, and if so, delete it."""
        current_time = datetime.now()
        for i in self._get_users():
            if datetime.strptime(i[1], '%A, %d. %B %Y %H:%M') < current_time - timedelta(hours=1):
                self.database.delete(f"DELETE FROM users WHERE id='{i[0]}'")

    @classmethod
    def _get_users(cls) -> list[tuple]:
        """Get all users that haven't confirmed their emails yet."""
        users = cls.database.get_all("SELECT id, registration_date FROM users WHERE status='0'")
        return users
