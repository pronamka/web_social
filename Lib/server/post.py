from Lib.updates.database import DataBase


class Post:
    """Post object with it's properties"""
    def __init__(self, post_id: int) -> None:
        self.database = DataBase()
        self.post_id = post_id
        self.title, self.creation_date = self._build_post()

    def _build_post(self) -> tuple:
        try:
            info = self.database.get_information(f"SELECT title, date FROM posts WHERE post_id='{self.post_id}'")
            return info
        except TypeError:
            assert False, """Post with such id does not exist. If you encountered this error,
             please contact us at defender0508@gmeail.com"""

    @property
    def get_title(self) -> str:
        return self.title

    @property
    def get_creation_date(self) -> str:
        return self.creation_date

    def __repr__(self) -> str:
        return f"""{self.__class__.__name__}{self.post_id, self.title, self.creation_date}"""

