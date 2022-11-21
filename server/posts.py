from abc import ABC, abstractmethod
from typing import Optional, Union
from datetime import datetime
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

    def __init__(self, comment_id: int, with_replies: bool = False):
        self.comment_id = comment_id
        self.post_id, self.user_id, self.text, self.date = self._get_properties()
        self.author = self._get_by_id()
        self.made_ago = str(datetime.now() - datetime.strptime(self.date, '%A, %d. %B %Y %H:%M')).split(', ', 1)[0]
        if with_replies:
            self.replies_amount = self._fetch_replies_amount()

    def _fetch_replies_amount(self) -> int:
        has_replies = self.database.get_information(f"SELECT COUNT(post_id) FROM comments "
                                                    f"WHERE is_reply={self.comment_id}")
        return has_replies if has_replies else 0

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

    @property
    def get_replies_amount(self):
        return self.replies_amount

    def __repr__(self) -> str:
        parameters_string = ''
        for attr in self.__dict__.items():
            parameters_string += f"{attr[0]} = {attr[1]}, "

        return f'{self.__class__.__name__}({parameters_string})'


class CommentsRegistry:
    database = DataBase()
    base_request = 'SELECT comment_id FROM comments WHERE status!=3 AND {conditions} ' \
                   'ORDER BY comment_id DESC LIMIT {amount} OFFSET {start_with}'

    comments_request = "WITH post_ids AS (SELECT post_id FROM posts WHERE verified!=2 AND user_id={of_user} " \
                       "ORDER BY post_id DESC) SELECT comment_id FROM comments " \
                       "WHERE post_id IN post_ids AND status!=3 AND is_reply==0 ORDER BY " \
                       "comment_id DESC LIMIT {amount} OFFSET {start_with}"

    objects = {'comment': 'post_id={} AND is_reply=0', 'reply': 'is_reply={}'}

    @classmethod
    def fetch_(cls, object_type: str, object_id: int,
               amount: int, start_with: int):
        conditions = cls.objects.get(object_type, '').format(object_id)
        request = cls.base_request.format(conditions=conditions, amount=amount,
                                          start_with=start_with)
        return [Comment(i, True) for i in cls.database.get_all_singles(request)]

    @classmethod
    def fetch_comments_on_users_post(cls, amount: int, start_with: int, of_user: int):
        formatted_request = cls.comments_request.format(of_user=of_user,
                                                        amount=amount, start_with=start_with)
        res = cls.database.get_all_singles(formatted_request)
        return [Comment(i) for i in res]


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
        if os.path.exists('static/avatar_images/' + str(self.get_author_id) + '.jpeg'):
            return 'avatar_images/' + str(self.get_author_id) + '.jpeg'
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
    default_request = 'SELECT post_id FROM posts {conditions} ORDER BY post_id ' \
                      'DESC LIMIT {amount} OFFSET {start_with}'

    @classmethod
    def get_posts(cls, amount: int, start_with: int,
                  parameters: dict = None, retrieve: str = 'post',
                  post_type: [PostForDisplay, FullyFeaturedPost] = PostForDisplay) -> list:
        """This method was described in the parent class."""
        request = cls.default_request.format(conditions=cls.process_conditions(parameters),
                                             amount=amount, start_with=start_with)
        ids = cls.database.get_all_singles(request)
        if retrieve == 'post':
            return [post_type(post_id) for post_id in ids]
        elif retrieve == 'id':
            return list(ids)

    @staticmethod
    def process_conditions(parameters: dict) -> str:
        if not parameters:
            return ''
        params = {'of_user': 'user_id={}', 'verified': 'verified==1',
                  'from_subscriptions': 'user_id IN {}'}
        conditions = 'WHERE '

        for iteration, item in enumerate(parameters.items()):
            conditions += params.get(item[0]).format(item[1])
            if iteration < len(parameters) - 1:
                conditions += ' AND '
        return conditions

    @classmethod
    def get_subscription_posts(cls, follows: tuple, amount: int, start_with: int) -> list[dict]:
        """Get posts of some users on a specific date.
        :param follows: a tuple with id's of users, whose posts are needed.
        :param amount: the amount of posts required.
        :param start_with: the amount of posts that will be excluded
                           from the output"""
        if len(follows) == 1:
            follows = (0, follows[0])
        data = cls.database.get_all(f'SELECT post_id, date FROM posts WHERE user_id IN {follows} '
                                    f'ORDER BY post_id DESC LIMIT {amount} OFFSET {start_with}')
        return [{i[1]: PostForDisplay(i[0])} for i in data]

    @classmethod
    def get_posts_from_ids(cls, post_ids: list,
                           post_type: Union[PostForDisplay, FullyFeaturedPost] = PostForDisplay) -> list:
        """Get objects of a specific type (default PostForDisplay), that contains
        information about the post, by their ids."""
        return [post_type(i) for i in post_ids]


class AdminPostRegistry(PostRegistry):

    @classmethod
    def get_posts(cls, amount: int, start_with: int) -> list:
        """The only difference between this method and
        get_posts method of UserPostRegistry is that here
        FullyFeaturedPost is yielded instead of PostForDisplay."""
        data = cls.database.get_all_singles(f'SELECT post_id FROM posts WHERE verified="0" ORDER BY '
                                            f'post_id LIMIT {amount} OFFSET {start_with}')
        return [FullyFeaturedPost(post_id) for post_id in data]
