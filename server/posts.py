from abc import ABC, abstractmethod
from typing import Optional, Union
import os

from server.database import DataBase


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
        self.author, self.display_date = self._find_data()

    def _find_data(self) -> tuple[str, str]:
        """Get the author and the accurate creation date of the post.
        First gets the author if from db, then calls _get_by_id() to get the actual name"""
        data = self.database.get_information(f'SELECT user_id, display_date '
                                             f'FROM posts WHERE post_id="{self.post_id}"')
        return self._get_by_id(data[0]), data[1]

    def _get_by_id(self, user_id: int) -> str:
        """Get the login and creation date of the post with given id.
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
        self.comments = {}
        self.counter = 0
        self.fetch_comments(5)

    def fetch_comments(self, amount: int) -> None:
        res = self.database.get_all_singles(f'SELECT comment_id FROM comments '
                                            f'WHERE post_id="{self.post_id}"'
                                            f' ORDER BY comment_id DESC LIMIT {amount} '
                                            f'OFFSET {self.counter}')
        for i in res:
            self.comments[self.counter] = Comment(i)
            self.counter += 1

    def get_latest_comments(self, amount: int, start_with: int) -> tuple:
        """Get available_comment defined amount of user's posts starting from the latest one."""
        if available_comments := self._check_comments_sufficiency(amount, start_with):
            comments = tuple(self.comments.values())[start_with:available_comments + start_with]
            return comments

    def _check_comments_sufficiency(self, amount: int, start_with: int) -> Optional[int]:
        """Check if there is enough posts to return.
        If not, attempt will be made to load some new ones.
        If there is still not enough to return even one None will be returned."""
        if (overall_amount := amount + start_with) > self.counter:
            self.fetch_comments(overall_amount - self.counter)
        if (comments_available := (self.counter - amount)) <= 0 and start_with > self.counter:
            return
        elif start_with < self.counter and comments_available <= 0:
            return self.counter - start_with
        elif overall_amount > self.counter and overall_amount > 0:
            return overall_amount
        else:
            return amount

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
    """PostForDisplay with author id and avatar."""

    def __init__(self, post_id: int) -> None:
        super().__init__(post_id)
        self.author_id = self._define_author_id()
        self.author_avatar = self._get_author_avatar()

    def _define_author_id(self):
        return self.database.get_information(f'SELECT id FROM '
                                             f'users WHERE login="{self.get_author}"')[0]

    def _get_author_avatar(self):
        if os.path.exists('static/avatar_images/'+str(self.get_author_id)+'.jpeg'):
            return 'avatar_images/'+str(self.get_author_id)+'.jpeg'
        else:
            return 'avatar_images/0.jpeg'

    @property
    def get_author_avatar(self):
        return self.author_avatar

    @property
    def get_author_id(self):
        return self.author_id


class PostRegistry(ABC):
    database = DataBase()

    @classmethod
    @abstractmethod
    def get_posts(cls, amount: int, start_with: int):
        """Get a certain amount of posts starting from a defined point,
        moving from the latest to the oldest.
        :param amount: the amount of posts you want to get.
        :param start_with: the starting point from the end of the posts table.
        For example if you want to get 10 latest post you pass 10 as amount,
        and 0 as starting point; Then, if you want to get another ten,
        you again pass 10 as amount and 10 as the starting point."""


class UserPostRegistry(PostRegistry):

    @classmethod
    def get_posts(cls,
                  amount: int,
                  start_with: int,
                  author_id: int = None,
                  post_type: [PostForDisplay, FullyFeaturedPost] = PostForDisplay):
        """This method was described in the parent class."""
        if not author_id:
            data = cls.database.get_all_singles(f'SELECT post_id FROM posts ORDER BY '
                                                f'post_id DESC LIMIT {amount} OFFSET {start_with}')
        else:
            data = cls.database.get_all_singles(f'SELECT post_id FROM posts WHERE user_id="{author_id}" ORDER BY '
                                                f'post_id DESC LIMIT {amount} OFFSET {start_with}')
        posts = [post_type(post_id) for post_id in data]
        return posts

    @classmethod
    def get_subscription_posts(cls, date: str, follows: tuple[int]):
        """Get posts of some users on a specific date.
        :param date: a string in format 'YYYY-MM-DD'
        :param follows: a tuple with id's of users, whose posts are needed."""
        if len(follows) == 1:
            follows = (0, follows[0])
        data = cls.database.get_all_singles(f'SELECT post_id FROM posts WHERE user_id IN {follows} '
                                            f'AND date="{date}"')
        posts = [PostForDisplay(post_id) for post_id in data]
        return posts

    @classmethod
    def get_posts_from_ids(cls, post_ids: list,
                           post_type: Union[PostForDisplay, FullyFeaturedPost] = PostForDisplay):
        """Get objects of a specific type (default PostForDisplay), that contains
        information about the post, by their ids."""
        return [post_type(i) for i in post_ids]


class AdminPostRegistry(PostRegistry):

    @classmethod
    def get_posts(cls, amount: int, start_with: int):
        """The only difference between this method and
        get_posts method of UserPostRegistry is that here
        FullyFeaturedPost is yielded instead of PostForDisplay."""
        counter = 0
        data = cls.database.get_all_singles(f'SELECT post_id FROM posts WHERE verified="0" ORDER BY '
                                            f'post_id DESC LIMIT {amount} OFFSET {start_with}')
        posts = [FullyFeaturedPost(post_id) for post_id in data]
        while counter < len(posts):
            yield posts[counter]
            counter += 1
