from Lib.server.database import DataBase

#  may be a custom PostNotFound exception should be implemented


class Post:
    """Basic representation of a user's publication."""
    database = DataBase()

    def __init__(self, post_id: int) -> None:
        self.post_id = post_id
        self.title, self.creation_date = self._build_post()

    def _build_post(self) -> tuple:
        info = self.database.get_information(f"SELECT title, date FROM posts WHERE post_id='{self.post_id}'")
        assert info is not None, 'Post with such id does not exist. If you encountered this error, ' \
                                 'please contact us at defender0508@gmeail.com'
        return info

    @property
    def get_title(self) -> str:
        return self.title

    @property
    def get_creation_date(self) -> str:
        return self.creation_date

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(post_id={self.post_id}, ' \
               f'title={self.title}, ' \
               f'creation_date={self.creation_date})'


class PostForDisplay(Post):
    def __init__(self, post_id: int) -> None:
        super(PostForDisplay, self).__init__(post_id)
        self.author = self._find_author()

    def _find_author(self) -> str:
        user_id = self.database.get_information(f'SELECT user_id FROM posts WHERE post_id="{self.post_id}"')[0]
        return self._get_by_id(user_id)

    def _get_by_id(self, user_id: int) -> str:
        return self.database.get_information(f'SELECT login FROM users WHERE id="{user_id}"')[0]

    @property
    def get_author(self) -> str:
        return self.author

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(post_id={self.post_id}, ' \
               f'title={self.title}, ' \
               f'creation_date={self.creation_date}, ' \
               f'author={self.author})'


'''class Post:
    """Post object with it's properties"""
    def __init__(self, post_id: int, with_author: bool = False) -> None:
        self.database = DataBase()
        self.post_id = post_id
        if with_author:
            self.title, self.creation_date = self._get_full_info()
        else:
            self.title, self.creation_date = self._get_post()
            self.author: str

    def _get_post(self) -> tuple:
        try:
            info = self.database.get_information(f"SELECT title, date FROM posts WHERE post_id='{self.post_id}'")
            return info
        except TypeError:
            assert False, """Post with such id does not exist. If you encountered this error,
             please contact us at defender0508@gmeail.com"""

    def _get_full_info(self) -> tuple:
        try:
            info = self.database.get_information(f"SELECT user_id, title, date FROM posts WHERE "
                                                 f"post_id='{self.post_id}'")

            return info
        except TypeError:
            assert False, """Post with such id does not exist. If you encountered this error,
             please contact us at defender0508@gmeail.com"""

    def _get_by_id(self, user_id):
        login = self.database.get_information(f'SELECT login FROM users WHERE id="{user_id}"')
        return login

    def _set_author(self, *args):
        self.author = self.database.get_information(f'SELECT login FROM users WHERE id="{args[0]}"')

    @property
    def get_title(self) -> str:
        return self.title

    @property
    def get_creation_date(self) -> str:
        return self.creation_date

    def __repr__(self) -> str:
        return f"""{self.__class__.__name__}{self.post_id, self.title, self.creation_date}"""'''
