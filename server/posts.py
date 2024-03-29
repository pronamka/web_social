from abc import ABC, abstractmethod
from typing import Union, Type
from datetime import datetime
from ast import literal_eval
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
        return f'upload_folder/articles/{self.post_id}.pdf'

    @property
    def get_preview(self) -> str:
        return f'upload_folder/previews/{self.post_id}.png'

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
        self.post_id, self.user_id, self.text, self.date, self.status = self._get_properties()
        self.author = self._get_by_id()
        self.author_avatar = self._get_author_avatar()
        self.made_ago = str((datetime.now() - datetime.strptime(self.date, '%A, %d. %B %Y %H:%M')).days)
        self.post_title = self._fetch_post_title()
        if with_replies:
            self.replies_amount = self._fetch_replies_amount()

    def _fetch_replies_amount(self) -> int:
        has_replies = self.database.get_information(f"SELECT COUNT(post_id) FROM comments "
                                                    f"WHERE is_reply={self.comment_id}")
        return has_replies if has_replies else 0

    def _get_properties(self) -> tuple:
        return self.database.get_information(f'SELECT post_id, user_id, comment, date, status FROM '
                                             f'comments WHERE comment_id="{self.comment_id}"')

    def _get_by_id(self) -> str:
        return self.database.get_information(f'SELECT login FROM users WHERE id="{self.user_id}"')[0]

    def _get_author_avatar(self):
        return t if (os.path.exists(t := f'static/avatar_images/{self.user_id}.jpeg')) else \
            'static/avatar_images/0.jpeg'

    def _fetch_post_title(self) -> str:
        return UserPostRegistry.get_posts_from_ids([self.post_id])[0].get_title

    @property
    def get_post_title(self) -> str:
        return self.post_title

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


class FullyFeaturedPost(PostForDisplay):
    """PostForDisplay with author id and avatar."""

    def __init__(self, post_id: int) -> None:
        super().__init__(post_id)
        info = self._get_info()
        self.author_id: int = info[0]
        self.tags: dict = literal_eval(info[1]) if info[1] else {}
        self.author_avatar = self._get_author_avatar()

    def _get_info(self):
        return self.database.get_information(f'SELECT user_id, tags FROM '
                                             f'posts WHERE post_id="{self.post_id}"')

    def _get_author_avatar(self):
        if os.path.exists('static/avatar_images/' + str(self.get_author_id) + '.jpeg'):
            return 'avatar_images/' + str(self.get_author_id) + '.jpeg'
        else:
            return 'avatar_images/0.jpeg'

    def _flatten_tags(self, tags: dict = None) -> list:
        """Flatten post's interest tags. This method can be used to also
        flatten any dictionary of dictionaries, if all leafs are just empty dictionaries.
        Otherwise, it will raise AttributeError."""
        if tags is None:
            tags = {}
        tags_plain = []
        for i in tags.keys():
            tags_plain.append(i)
            if (t := tags.get(i, None)) != {}:
                tags_plain += self._flatten_tags(t)
        return tags_plain

    def get_tags(self, flattened: bool = False) -> Union[list, dict]:
        """Get post's interest tags. They can be returned either in their initial form with
        nesting or as a flat list, if flattened is True."""
        if flattened:
            return self._flatten_tags(self.tags)
        else:
            return self.tags

    @property
    def get_author_avatar(self) -> str:
        return self.author_avatar

    @property
    def get_author_id(self) -> int:
        return self.author_id


class PostExtended(FullyFeaturedPost):

    def __init__(self, post_id: int, with_views_and_likes: bool = True,
                 with_author_subscribers: bool = True):
        super().__init__(post_id)
        self.tags_flattened = self._flatten_tags(self.tags)
        self.made_ago = self._calculate_time()
        self.made_ago_str = self._get_str_representation(self.made_ago)
        if with_views_and_likes:
            self.views_amount = self._get_views_amount()
            self.likes_amount = self._get_likes_amount()
        if with_author_subscribers:
            self.author_subscribers = self._get_author_subscribers()

    def _get_author_subscribers(self) -> list:
        return self.database.get_all(f'SELECT subscriber_id FROM subscriptions WHERE '
                                     f'author_id={self.author_id}')

    def _get_views_amount(self) -> int:
        return self.database.get_information(f'SELECT COUNT(user_id) FROM post_views '
                                             f'WHERE post_id={self.post_id}')[0]

    def _get_likes_amount(self) -> int:
        return self.database.get_information(f'SELECT COUNT(user_id) FROM post_likes '
                                             f'WHERE post_id={self.post_id}')[0]

    def _calculate_time(self) -> dict:
        made_ago = (datetime.now() - datetime.strptime(self.creation_date,
                                                       '%Y-%m-%d')).total_seconds()
        return self._get_time_periods(int(made_ago))

    @staticmethod
    def _get_time_periods(total_seconds: int) -> dict:
        periods_in_seconds = [31104000, 2592000, 86400, 3600, 60]
        time_periods = ['years', 'months', 'days', 'hours', 'minutes']
        periods_duration = {}
        for period_name, period_seconds in zip(time_periods, periods_in_seconds):
            periods_duration[period_name] = total_seconds // period_seconds
            total_seconds -= periods_duration[period_name]*period_seconds
        periods_duration['seconds'] = total_seconds
        return periods_duration

    @staticmethod
    def _get_str_representation(time_period_durations: dict) -> str:
        str_representation = 'Made '
        for period, duration in time_period_durations.items():
            str_representation += str(duration) + ' ' + period + ', ' if duration else ''
        return str_representation.removesuffix(', ') + ' ago'

    @property
    def get_subscribers_amount(self) -> int:
        return len(self.author_subscribers)


class CommentsRegistry:
    database = DataBase()
    base_request = 'SELECT comment_id FROM comments WHERE {show_banned} {conditions} ' \
                   'ORDER BY comment_id DESC LIMIT {amount} OFFSET {start_with}'

    comments_request = "WITH post_ids AS (SELECT post_id FROM posts WHERE verified!=2 AND user_id={of_user} " \
                       "ORDER BY post_id DESC) SELECT comment_id FROM comments " \
                       "WHERE post_id IN post_ids AND status == {comment_status} AND is_reply==0 ORDER BY " \
                       "comment_id DESC LIMIT {amount} OFFSET {start_with}"

    objects = {'comment': 'post_id={} AND is_reply=0', 'reply': 'is_reply={}'}

    @classmethod
    def fetch_(cls, object_type: str, object_id: int,
               amount: int, start_with: int, show_banned: bool = False) -> list:
        show_banned = '' if show_banned else 'status!=3 AND'
        conditions = cls.objects.get(object_type, '').format(object_id)
        request = cls.base_request.format(conditions=conditions, amount=amount,
                                          start_with=start_with, show_banned=show_banned)
        return [Comment(i, True) for i in cls.database.get_all_singles(request)]

    @classmethod
    def fetch_comments_on_users_post(cls, amount: int, start_with: int, of_user: int,
                                     comment_status: int = 0) -> list:
        formatted_request = cls.comments_request.format(of_user=of_user,
                                                        amount=amount, start_with=start_with,
                                                        comment_status=comment_status)
        res = cls.database.get_all_singles(formatted_request)
        return [Comment(i, True) for i in res]

    @classmethod
    def find_comment(cls, user_id: int, post_id: int, text: str, is_reply: int) -> Comment:
        return Comment(DataBase().get_information(
            f'SELECT comment_id FROM comments WHERE user_id={user_id} AND '
            f'post_id={post_id} AND comment="{text}" AND is_reply={is_reply}', (0, ))[0], True)


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
    post_types = {0: PostForDisplay, 1: FullyFeaturedPost, 2: PostExtended}

    @classmethod
    def get_posts(cls, amount: int, start_with: int,
                  parameters: dict = None, retrieve: str = 'post',
                  post_type: int = 1) -> list:
        """This method was described in the parent class."""
        request = cls.default_request.format(conditions=cls.process_conditions(parameters),
                                             amount=amount, start_with=start_with)
        ids = cls.database.get_all_singles(request)
        if retrieve == 'post':
            return [cls.post_types.get(post_type, PostForDisplay)(post_id) for post_id in ids]
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
        return [{i[1]: PostExtended(i[0])} for i in data]

    @classmethod
    def get_posts_from_ids(cls, post_ids: list,
                           post_type: Type[Union[PostForDisplay,
                                                 FullyFeaturedPost, PostExtended]] = PostForDisplay) -> list:
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
        return [PostExtended(post_id) for post_id in data]
