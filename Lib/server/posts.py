from Lib.server.database import DataBase


#  may be a custom PostNotFound exception should be implemented


class Post:
    """Basic representation of a user's publication.
    :param post_id: an id of a post that should be created,
                    if there is no post with given id AssertionError will be raised."""
    database = DataBase()

    def __init__(self, post_id: int) -> None:
        self.post_id = post_id
        self.title, self.creation_date = self._build_post()

    def _build_post(self) -> tuple:
        """Get all the post data from database.
        :raises AssertionError: if there is no post with given id"""
        info = self.database.get_information(f"SELECT title, date FROM posts WHERE post_id='{self.post_id}'")
        assert info is not None, 'Post with such id does not exist. If you encountered this error, ' \
                                 'please contact us at defender0508@gmeail.com'
        return info

    @property
    def get_id(self) -> int:
        return self.post_id

    @property
    def get_path(self) -> str:
        return f'upload_folder/{self.title}'

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
        """Get the author of the post.
        First gets the author if from db, then calls _get_by_id() to get the actual name"""
        user_id = self.database.get_information(f'SELECT user_id FROM posts WHERE post_id="{self.post_id}"')[0]
        return self._get_by_id(user_id)

    def _get_by_id(self, user_id: int) -> str:
        """Get the login of the user with given id.
        :param user_id: integer representing an id of a user"""
        return self.database.get_information(f'SELECT login FROM users WHERE id="{user_id}"')[0]

    @property
    def get_author(self) -> str:
        return self.author

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(post_id={self.post_id}, ' \
               f'title={self.title}, ' \
               f'creation_date={self.creation_date}, ' \
               f'author={self.author})'


class Comment:
    """Comment object.
    :param comment_id: integer representing an id of a comment that should be presented"""
    database = DataBase()

    def __init__(self, comment_id: int):
        self.comment_id = comment_id
        self.post_id, self.user_id, self.text, self.date = self._get_properties()
        self.author = self._get_by_id()

    def _get_properties(self) -> tuple:
        return self.database.get_information(f'SELECT post_id, user_id, comment, date FROM '
                                             f'comments WHERE comment_id="{self.comment_id}"')

    def _get_by_id(self) -> str:
        return self.database.get_information(f'SELECT login FROM users WHERE id="{self.user_id}"')[0]

    @property
    def get_author(self) -> str:
        return self.author

    @property
    def get_text(self) -> str:
        return self.text

    def __repr__(self) -> str:
        parameters_string = ''
        for attr in self.__dict__.items():
            parameters_string += f"{attr[0]} = {attr[1]}, "

        return f'{self.__class__.__name__}({parameters_string})'


class CommentsRegistry:
    """Registry that keeps record of all comments of a post."""
    database = DataBase()

    def __init__(self, post_id: int) -> None:
        self.post_id = post_id
        self.comments = self.define_comments()
        self.counter = 0

    def define_comments(self, amount: int = 20) -> dict[int: Comment]:
        """Get all the the comments from database."""
        comment_ids = self.database.get_many_singles(f'SELECT comment_id FROM comments '
                                                     f'WHERE post_id="{self.post_id}"', size=amount)
        comments = {comment_id: Comment(comment_id) for comment_id in comment_ids}
        return comments

    def __iter__(self):
        return self

    def __next__(self) -> Comment:
        if self.counter >= len(self.comments):
            self.counter = 0
            raise StopIteration
        else:
            self.counter += 1
            return list(self.comments.values())[self.counter - 1]

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(post_id={self.post_id}, comments={self.comments})'


class FullyFeaturedPost(PostForDisplay):
    """PostForDisplay with a CommentRegistry
    to access all comments on this post through it."""

    def __init__(self, post_id: int) -> None:
        super().__init__(post_id)
        self.comment_registry = CommentsRegistry(self.post_id)

    @property
    def get_comments(self) -> CommentsRegistry:
        return self.comment_registry


class PostRegistry:
    database = DataBase()

    @classmethod
    def get_posts(cls, amount: int, start_with: int):
        counter = 0
        data = cls.database.get_all_singles(f'SELECT post_id FROM posts ORDER BY '
                                            f'post_id DESC LIMIT {amount} OFFSET {start_with}')
        posts = [PostForDisplay(post_id) for post_id in data]
        while counter < len(posts):
            yield posts[counter]
            counter += 1


class AdminPostRegistry:
    database = DataBase()
    #  need to add a system to verify posts
    #  posts that are verified should not get displayed on the admins page

    @classmethod
    def get_posts(cls, amount: int, start_with: int):
        counter = 0
        data = cls.database.get_all_singles(f'SELECT post_id FROM posts ORDER BY '
                                            f'post_id DESC LIMIT {amount} OFFSET {start_with}')
        posts = [FullyFeaturedPost(post_id) for post_id in data]
        while counter < len(posts):
            yield posts[counter]
            counter += 1

