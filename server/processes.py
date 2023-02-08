from typing import Union, Any, Callable, Optional
from enum import Enum
from datetime import datetime, timedelta
from json import dumps, JSONEncoder
from abc import ABC, abstractmethod
from functools import wraps
from ast import literal_eval

from flask import request, render_template, url_for, session, abort, redirect
from flask_login import login_user
from flask_mail import Mail, Message

from werkzeug.security import generate_password_hash, check_password_hash

from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadTimeSignature

from server.app_core import app, users
from server.database import DataBase
from server.posts import AdminPostRegistry, UserPostRegistry, \
    FullyFeaturedPost, CommentsRegistry, PostExtended
from server.user import UserFactory, Viewer, Author, Admin, UserRole
from server.managers import Manager
from server.search_engine import Searcher


class RegistrationState(Enum):
    """Represents possible conditions of registration process."""
    LoginAlreadyExists = 0
    FieldsNotFilled = 1
    CredentialsFine = 2
    SuccessfullyCreated = 3


class LogInState(Enum):
    """Represents possible conditions of the process of logging in."""
    WrongCredentials = 1
    UserAlreadyLoggedIn = 2
    EmailNotConfirmed = 3
    CredentialsFine = 4
    AdminUser = 5


class Encoder(JSONEncoder):
    """Class for encoding objects, that are not
    serializable by default."""

    def default(self, o: Any) -> Any:
        return o.__dict__


def login_required(current_session):
    """
    If you decorate a view with this, it will ensure that the current user is
    logged in and authenticated before calling the actual view.
    Note: this method is taken from flask-login library and slightly re-written
    to fit the system. Do not import this function from flask-login to avoid errors."""

    def decorated_view(function: Callable):
        @wraps(function)
        def fixed_decorated_view(*args, **kwargs):
            if request.method in {"OPTIONS"} or app.config.get("LOGIN_DISABLED"):
                pass
            elif (login := current_session.get('login', None)) and not users.get(login, None):
                return "<h1>Oops...</h1>" \
                       "<h2>It's our fault!</h2>" \
                       "<h4>Sorry, it looks like we had to relaunch the server," \
                       "while you were logged in. Please follow this link to go to " \
                       "the log in page: <a href='/log_in_page'>Go to log in page</a></h4>"
            elif not current_session.get('login', None):
                return redirect('/log_in_page')

            # flask 1.x compatibility
            # current_app.ensure_sync is only available in Flask >= 2.0
            if callable(getattr(app, "ensure_sync", None)):
                return app.ensure_sync(function)(*args, **kwargs)
            return function(*args, **kwargs)

        return fixed_decorated_view

    return decorated_view


def admin_required(func: Callable):
    """Check if the user that is trying to enter
    a url is admin. If he is not, his attempt will
    be aborted with http status code 418."""

    @wraps(func)
    def wrapper():
        if get_user().get_role == UserRole.Admin:
            try:
                return func()
            except AssertionError as e:
                return {'status': f'{e.__class__.__name__}: {e}'}
        else:
            return abort(418)

    return wrapper


def author_required(func: Callable):
    """Check if the user that is trying to commit
    a certain action is an author."""

    @wraps(func)
    def wrapper(*args):
        if get_user().get_role == UserRole.Viewer:
            return 0
        else:
            if args:
                return func(args[0], *args[1:-1])
            else:
                return func()

    return wrapper


def get_user() -> Union[Viewer, Author, Admin]:
    """Get the user object that corresponds with the client machine."""
    return users.get(session.get('login'))


def search_for(query: str, required_amount: int = 5, start_with=0, strictly: bool = False):
    """General function to search for posts and get information
    about them."""
    post_ids = Searcher.search(query, limit=required_amount, start_with=start_with,
                               strictly=strictly, interests=get_user().get_interests)
    res = {'search_results': UserPostRegistry.get_posts_from_ids(post_ids[0], post_type=PostExtended),
           'searched_for': post_ids[1]}
    return dumps(res, cls=Encoder)


def write_comment(post_id: int, comment_text: str, is_reply: int = None):
    """Add a comment to a certain post.
    :param post_id: the id of the post under which a comment was left.
    :param comment_text: the text of the comment.
    :param is_reply: determines if the comment is a reply to another comment (it
    equals to 0 if it is not or to an id of another comment, if it is)."""
    current_user = get_user()
    if is_reply and current_user.get_role == UserRole.Author and \
            current_user.PostManager.check_comment_belonging(is_reply):
        current_user.author_reply(post_id, comment_text, is_reply)
    else:
        current_user.add_comment(post_id, comment_text, is_reply)
    return dumps(CommentsRegistry.find_comment(current_user.user_id, post_id, comment_text, is_reply), cls=Encoder)


def check_password(user_id: int, password: str) -> bool:
    if not check_password_hash(DataBase(access_level=1).get_information(f'SELECT password FROM users '
                                                                        f'WHERE id={user_id}', (False,))[0], password):
        return False
    else:
        return True


class PostAnalyticsBuilder:
    database = DataBase()
    standard_request = 'WITH list(post_id, title) AS (VALUES {values})\
                        SELECT post_id, title, IFNULL(COUNT(user_id), 0) AS amount\
                        FROM list LEFT JOIN {table_name} USING (post_id) GROUP BY post_id;'

    over_time_request = 'WITH l(user_id, created_on) AS (SELECT user_id, created_on FROM {table_name} ' \
                        'WHERE post_id IN {post_ids}), list(created_on) AS (VALUES {dates}) ' \
                        'SELECT created_on, IFNULL(COUNT(user_id), 0) AS amount ' \
                        'FROM list LEFT JOIN l USING (created_on) GROUP BY list.created_on'

    @classmethod
    def _get_posts(cls, user_id: int, limit: int = -1, offset: int = 0) -> list:
        """Get a list of tuples containing ids and titles of posts in range,
        specified by limit and offset."""
        posts = cls.database.get_all(f'SELECT post_id, title FROM posts WHERE user_id={user_id} '
                                     f'ORDER BY post_id DESC LIMIT {limit} OFFSET {offset}')
        return posts

    @classmethod
    def _get_any(cls, query: str, properties: list[str]) -> list[tuple]:
        """Get a list of tuples containing any information specified in query.
        Used to apply the same sql query to multiple tables in cases where JOIN is not
        suitable.
        :param query: an sql query, that contains the substring: `{}`; it will be formatted
                      to fetch data from different tables.
        :param properties: a list of strings that represent table names. The given query
                           will be executed `range(len(properties))` times, fetching data
                           from one table at a time. """
        for i in properties:
            yield cls.database.get_all(query.format(i))

    @classmethod
    def on_post_activity(cls, user_id, limit: int = 30, offset: int = 0) -> dict[str: list]:
        """Get the amount of views, likes, comments on each of the latest posts in
        range, specified by limit and offset."""
        analytics = {'views': [], 'likes': [], 'comments': []}
        all_info: list = cls._get_posts(user_id, limit, offset)
        if not all_info:
            return analytics
        req = cls.standard_request.format(values=str(all_info).removeprefix('[').removesuffix(']'),
                                          table_name='{}')
        views, likes, comments = cls._get_any(req, ['post_views', 'post_likes', 'comments'])
        for view, like, comment in zip(views, likes, comments):
            analytics.get('views').append({'x': view[1], 'y': view[2]})
            analytics.get('likes').append({'x': like[1], 'y': like[2]})
            analytics.get('comments').append({'x': comment[1], 'y': comment[2]})
        return analytics

    @classmethod
    def _get_all_post_ids(cls, user_id: int) -> tuple[int]:
        """Get a tuple with ids of all posts user ever made."""
        query = f'SELECT post_id FROM posts WHERE user_id={user_id}'
        return tuple(cls.database.get_all_singles(query))

    @classmethod
    def _get_each_day(cls, limit: int = 30, offset: int = 0) -> str:
        """Get dates in range from (today - offset) to (today - offset - limit),
        in format `('YYYY-MM-DD'), ('YYYY-MM-DD')`.
        This format is need to present data in the form that sqlite's temporary
        tables use."""
        now = (datetime.now() - timedelta(days=offset))
        delta = timedelta(days=1)
        all_dates = ''
        for _ in range(limit):
            all_dates += "('" + (now := (now - delta)).strftime('%Y-%m-%d') + "'), "
        return all_dates.removesuffix(', ')

    @classmethod
    def over_time_activity(cls, user_id, limit: int = 30, offset: int = 0) -> dict[str: list]:
        """Get the amount of views, likes, comments on all user's posts on each
        day in range specified by limit and offset."""
        analytics = {'views': [], 'likes': [], 'comments': []}
        days = cls._get_each_day(limit, offset)
        last_requested_date = datetime.strptime(days.rsplit("('")[1].removesuffix("'), "), '%Y-%m-%d')

        # if user requesting info from six month ago or older, return empty analytics
        if last_requested_date < (datetime.now() - timedelta(weeks=30)):
            return analytics
        req = cls.over_time_request.format(post_ids=str(cls._get_all_post_ids(user_id)),
                                           table_name='{}', dates=days)
        views, likes, comments = cls._get_any(req, ['post_views', 'post_likes', 'comments'])
        for view, like, comment in zip(views, likes, comments):
            analytics.get('views').append({'x': view[0], 'y': view[1]})
            analytics.get('likes').append({'x': like[0], 'y': like[1]})
            analytics.get('comments').append({'x': comment[0], 'y': comment[1]})
        return analytics


class InformationGetter:
    """Class for formalizing and getting information
    for loading content for pages (usually called by js on client)"""

    def __init__(self, properties: dict, **kwargs) -> None:
        """Initialize InformationGetter.
        :param properties: dictionary with all
            the information about what data is required.
        :param kwargs: dictionary with some special
            information for loading exact values
            (e.g. how many posts were already loaded
            and which to load now etc.). Not always required."""
        self.properties = properties
        self.parameters: dict = kwargs.get('parameters')
        self.user = get_user()
        self.protocols = {'subscribers': self.get_subscribers,
                          'commentaries_made': ...,
                          'commentaries_received': self.amount_of_commentaries_received_on_post,
                          'post_amount': self.amount_of_posts,
                          'latest_posts': self.get_latest_posts,
                          'dated_posts': self.get_dated_posts,
                          'latest_comments': self.get_latest_comments_or_replies,
                          'comments_for_authors': self.get_latest_comments_on_users_posts,
                          'interests': self.get_interests,
                          'avatar': self.get_avatar,
                          'analytics': self.get_analytics,
                          'overall_user_post_statistics': self.get_overall_post_statistics}

    def get_full_data(self) -> dict:
        """Get all the data that was specified
        when initializing the InformationGetter."""
        if not self.properties:
            return {}
        data = {}
        for i in self.properties.keys():
            if not isinstance(result := self.get_information(i), int) \
                    and self.properties.get(i) == 'amount':
                data[i] = len(result)
            else:
                data[i] = result
        return data

    def get_information(self, method: str) -> Union[tuple, list, int]:
        """Get information, if it's covered in protocols.
        :param method: a string defining which information
            is needed (a key to a dictionary with arguments)"""
        return self.protocols.get(method)()

    def _get_from_parameters(self, parameter_keys: dict) -> tuple:
        existing_keys = self.parameters.keys()
        res = tuple((parameter_keys[item] if item not in existing_keys else self.parameters.get(item))
                    for position, item in enumerate(parameter_keys))
        return res

    def get_overall_post_statistics(self):
        if self.user.get_role.value < 2:
            return 0
        else:
            return self.user.PostManager.get_overall_amounts(['views', 'likes', 'comments'])

    def get_analytics(self) -> dict[str: list]:
        analytics_protocols = {'over_time_activity': PostAnalyticsBuilder.over_time_activity,
                               'on_post_activity': PostAnalyticsBuilder.on_post_activity
                               }
        analytics_required = self._get_from_parameters({'chart': 'views_likes_comments',
                                                        'required': 30, 'loaded': 0})
        return analytics_protocols.get(analytics_required[0])(self.user.get_user_id, *analytics_required[1:3])

    def get_avatar(self) -> str:
        return self.user.get_avatar

    def get_interests(self) -> dict[str: dict]:
        if self._get_from_parameters({'all_interests': False})[0]:
            return {'interests': (t := literal_eval(open('server_settings.txt', mode='r').read()))
                    .get('all_interests', ''), 'descriptions': t.get('sciences_descriptions', '')}
        return self.user.get_interests

    def get_subscribers(self) -> list:
        return self.user.SubscriptionManager.get_followers

    def get_latest_comments_or_replies(self) -> list:
        post_id, amount, start_with, content_type = \
            self._get_from_parameters({'object_id': 0, 'comments_required': 1,
                                       'comments_loaded': 0, 'object_type': 'comment'})
        return CommentsRegistry.fetch_(content_type, post_id, amount, start_with)

    def get_latest_comments_on_users_posts(self) -> list:
        amount, start_with, status = self._get_from_parameters(
            {'comments_required': 0, 'comments_loaded': 0, 'comment_status': 0})
        return self.user.PostManager.get_latest_comments(amount, start_with, status)

    def get_latest_posts(self) -> Union[int, tuple[FullyFeaturedPost], list[FullyFeaturedPost]]:
        """Get any posts. Specific instructions are retrieved
        from parameters passed to the class constructor."""
        amount, start_with, of_user, post_type = self._get_from_parameters(
            {'posts_required': 1, 'posts_loaded': 0, 'of_user': True, 'post_type': 1})
        if of_user and self.user.get_role == UserRole.Viewer:
            return 0
        elif of_user:
            return self.user.PostManager.get_latest_posts(amount, start_with, post_type=post_type)
        else:
            return UserPostRegistry.get_posts(amount, start_with, {'verified': True}, post_type=post_type)

    @author_required
    def amount_of_commentaries_received_on_post(self) -> int:
        return self.user.PostManager.get_comments_amount(self.parameters.get('post_id'))

    @author_required
    def amount_of_posts(self) -> int:
        """Get the amount of post user made."""
        return self.user.PostManager.get_post_amount()

    def get_dated_posts(self) -> list:
        """Get the posts of the people the current user
        is subscribed to, sort them by date."""
        amount, start_with, post_type = self._get_from_parameters({'posts_required': 1, 'posts_loaded': 0,
                                                                   'post_type': 1})
        follows = fol if len((fol := self.user.SubscriptionManager.get_follows)) >= 2 else list(fol).append(0)
        posts = UserPostRegistry.get_posts(amount, start_with, {'from_subscriptions': follows, 'verified': True},
                                           post_type=post_type)
        return posts


class InformationLoader:
    """General class for getting information about posts and comments."""

    @staticmethod
    @app.route('/load_info/', methods=['GET', 'POST'])
    def load_info():
        """Get whatever info you want specified in protocols
        (info and other parameters should be passed as request arguments)"""
        params = request.json
        protocols = {
            'main_user_page': {'latest_posts': 'object'},
            'subscription_page': {'dated_posts': 'object'},
            'comments': {'latest_comments': 'object'},
            'hub': {'latest_posts': 'object',
                    'commentaries_received': 'amount',
                    'post_amount': 'object',
                    'subscribers': 'amount',
                    'overall_user_post_statistics': 'object'},
            'content': {'latest_posts': 'object'},
            'comment_section': {'comments_for_authors': 'object'},
            'personal_data': {'interests': 'object', 'avatar': 'object'},
            'analytics': {'analytics': 'object'}}
        data = InformationGetter(protocols.get(params.get('page')),
                                 parameters=params).get_full_data()
        return dumps(data, cls=Encoder)

    @staticmethod
    @app.route('/admin_get_posts/', methods=['GET', 'POST'])
    @admin_required
    def admin_get_posts() -> str:
        posts_loaded, posts_required = request.json.values()
        data = AdminPostRegistry.get_posts(posts_required, posts_loaded)
        return dumps(data, cls=Encoder)


class LogInHandler(Manager):
    """Class for conducting the logging in process."""

    def __init__(self) -> None:
        super(LogInHandler, self).__init__()
        self.status = None
        self.login = request.json.get('login')

    def force_log_in(self) -> None:
        """Log in a user, that already has an active session."""
        users.pop(session.get('login'))
        session.pop('login')
        self.log_user()

    def log_user(self) -> tuple:
        """General function that launches all the processes of logging in"""
        self._check_properties()
        if self.status.value >= 4:
            self._log_in(self.login)
        return self.status

    def _log_in(self, login: str) -> LogInState:
        """Update the user object,
        log it in, so it can pass through @login_required and add it to session."""
        info = self._find_by_login(login)
        # noinspection PyArgumentList
        users[login] = UserFactory.create_auto(info[0])
        self._add_to_session(login)
        return LogInState.CredentialsFine

    def _add_to_session(self, login: str) -> None:
        """Add a user to session."""
        login_user(users.get(login))
        session['login'] = login
        session['id'] = str(get_user().get_user_id)
        self._check_if_admin()

    def _find_by_login(self, login: str) -> tuple[int]:
        """Get the user's id from his login."""
        return self.database.get_information(f'SELECT id FROM users WHERE login="{login}"')

    def _check_if_admin(self):
        """Check if the user that is trying to log in is an admin.
        Admins get redirected to other pages automatically."""
        if get_user().get_role == UserRole.Admin:
            self.status = LogInState.AdminUser

    def _check_properties(self) -> None:
        """Check if all the user-given data is alright."""
        if self._find_user() == LogInState.WrongCredentials or self._check_password() is False:
            self.status = LogInState.WrongCredentials
        elif self.database.get_information(f'SELECT status FROM users WHERE '
                                           f'login="{self.login}"')[0] != 1:
            self.status = LogInState.EmailNotConfirmed
        elif (lg := session.get('login')) and lg != self.login:
            self.status = LogInState.UserAlreadyLoggedIn
        else:
            self.status = LogInState.CredentialsFine

    def _check_if_user_logged_in(self) -> bool:
        """Check whether the user logged in already.
        :returns: True if user is not logged in yet, False if he is."""
        if session.get('login') != self.login:
            return True
        else:
            return False

    def _find_user(self) -> LogInState:
        """Check if the user wth given login exist."""
        if not self.database.get_information(f"SELECT login FROM users WHERE login='{self.login}'"):
            return LogInState.WrongCredentials
        else:
            return LogInState.CredentialsFine

    def _check_password(self) -> bool:
        """Check if password hash stored in database matches the user-provided password.
        :returns: True if it matches, False if it does not"""
        return check_password_hash(self.database.get_information(f"SELECT PASSWORD FROM users WHERE "
                                                                 f"login='{self.login}'")[0],
                                   request.json.get('password'))


class RegistrationHandler:
    """Class for conducting the registration process."""

    #  WARNING: users can create different accounts with one email.
    #  This is only to make testing easier and should be fixed before deployment

    database = DataBase(access_level=2)

    def __init__(self, login: str, password: str, email: str) -> None:
        self.login: str = login
        self.password: str = password
        self.email = email
        self.status: RegistrationState = self._check_properties()
        self.error_messages = None

    @classmethod
    def resend_email(cls, login: str) -> None:
        """Resend email. If you want to send email to a specific user do not use this function
        as it will send the message to the email address of a RegistrationHandler instance"""
        email = cls.database.get_information(f'SELECT email FROM users '
                                             f'WHERE login="{login}" AND status=0')[0]
        email_confirmation_handler = EmailConfirmationHandler(login, email)
        email_confirmation_handler.send_email()

    def create_new_user(self) -> None:
        """General function that launches all the processes."""
        if self._check_status():
            self._create_in_db()
            email_confirmation_handler = EmailConfirmationHandler(self.login, self.email)
            email_confirmation_handler.send_email()
            self.status = RegistrationState.SuccessfullyCreated

    def _check_status(self) -> Union[RegistrationState, None]:
        """Check status of data before creating a use.r"""
        if self.status == RegistrationState.LoginAlreadyExists:
            self.error_messages = "Account with this name already exists. " \
                                  "Please give your account a different name."
        elif self.status == RegistrationState.FieldsNotFilled:
            self.error_messages = "Fill all the fields."
        else:
            return RegistrationState.CredentialsFine

    def _check_properties(self) -> RegistrationState:
        """Check if all the user-provided data is ok.
        :returns: RegistrationState.CredentialsFine if it is and None if it's not"""
        if self._check_login():
            return RegistrationState.LoginAlreadyExists
        elif self.login and self.password and self.email:
            return RegistrationState.CredentialsFine
        else:
            return RegistrationState.FieldsNotFilled

    def _create_in_db(self) -> None:
        """Creates the row in database containing user data."""
        user_data = self._build_data_package()
        query = "INSERT INTO users(login, password, email, registration_date) VALUES (?, ?, ?, ?);"
        self.database.insert(query, data=user_data)

    def _build_data_package(self) -> tuple:
        """Gathers all user data in one package."""
        password_hash = self._hash_password()
        creation_date = datetime.now().strftime("%A, %d. %B %Y %H:%M")
        user_data = (self.login, password_hash, self.email, creation_date)
        return user_data

    def _hash_password(self) -> str:
        """Hash user password as storing hash is much safer than storing passwords."""
        password_hash = generate_password_hash(self.password)
        del self.password
        return password_hash

    def _check_login(self) -> Union[RegistrationState, None]:
        """Check if user-provided login already exists."""
        if self.login in self.database.get_all_singles(f"SELECT login FROM users"):
            return RegistrationState.LoginAlreadyExists
        else:
            return None


class Token:
    """Class for working with tokens.
    You do not need to create instances of this class to use it."""

    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])  # this object is used to create and check tokens

    @classmethod
    def create_token(cls, user_id: int) -> str:
        """Create a token."""
        return cls.serializer.dumps(user_id, app.config['SECURITY_PASSWORD_SALT'])

    @classmethod
    def check_token(cls, token: str, expiration=1800) -> [int, bool]:
        """Check if a token is right and has not expired yet."""
        try:
            user_id = cls.serializer.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'],
                                           max_age=expiration)
            return user_id
        except BadTimeSignature:
            return False


class EmailSenderWithToken(ABC):
    """Class for sending emails that require token."""

    database = DataBase()

    def __init__(self, email_address: str):
        self.email_manager = Mail(app)
        self.email_address = email_address
        self.token = Token()
        self.user_id = self._get_by_email()

    @abstractmethod
    def send_email(self):
        """General function for building email message and
        sending it on the email address given when initializing."""

    @abstractmethod
    def _create_email(self):
        """Build the actual email message (usually html)"""

    @abstractmethod
    def _build_url(self):
        """Build the url that user should follow to complete whatever
        action described in child classes."""

    def _get_by_email(self) -> int:
        """Get user id from login."""
        return DataBase().get_information(f"SELECT id FROM users WHERE email="
                                          f"'{self.email_address}'")[0]


class EmailConfirmationHandler(EmailSenderWithToken):
    """Class for conducting the process of email confirmation."""

    def __init__(self, login: str, email: str) -> None:
        super().__init__(email)
        self.login = login

    @app.route('/send_email/<login>/<email>')
    def send_email(self) -> str:
        """Send the email message to its recipients."""
        email_message = self._create_email()
        self.email_manager.send(email_message)
        return render_template('registration_page.html')

    @staticmethod
    @app.route('/confirm_email/<token>')
    def confirm_email(token: str) -> str:
        """Check the token in the user's email message."""
        if (user_id := Token.check_token(token)) is False:
            return 'The link is either wrong or expired.'
        else:
            DataBase(access_level=3).update(f'UPDATE users SET status=1 WHERE id={user_id}')
            return 'Your account is confirmed, thanks. You can now close this page.'

    def _create_email(self) -> Message:
        """Build the actual email message (html)"""
        verification_message = Message('Confirm your email address', recipients=[self.email_address])
        verification_message.html = render_template('email_pages/confirmation_letter.html',
                                                    confirm_url=self._build_url())
        return verification_message

    def _build_url(self) -> str:
        """Build a url for a confirm_email() function."""
        return url_for('confirm_email', token=self.token.create_token(self.user_id), _external=True)


class RestorePasswordNotificationSender(EmailSenderWithToken):
    """Class for sending an email to restore password and
    actually restoring it."""

    def __init__(self, email_address: Optional[str] = None, login: Optional[str] = None):
        if login:
            email_address = self._get_email_by_login(login)
        super().__init__(email_address)

    def send_email(self) -> dict:
        """General function to send a message to restore password.
        Check if the user with given email(or login) exists and
        if he had confirmed his email address. If both conditions are
        true, a link, leading to a page for password restoration will
        be sent to the user's email address."""
        if not self.user_id:
            return {'status': 406, 'response': "The login or email you've entered does not exist."}
        if not self._check_if_email_confirmed():
            return {'status': 409, 'response': "You did not confirm your email yet."}
        email_message = self._create_email()
        self.email_manager.send(email_message)
        return {'status': 200}

    @staticmethod
    @app.route('/change_password/', methods=['POST'])
    def change_password() -> str:
        """Set user's password to the new one he chooses, if the
        token in the email sent to the user hasn't expired and if it's valid.
        Token and password both sent as a body of the request via js fetch()."""
        password, token = request.json.values()
        if (user_id := Token.check_token(token)) is False:
            return 'Oops... The link is no longer valid.'
        password = generate_password_hash(password)
        DataBase(access_level=3).update(f'UPDATE users SET '
                                        f'password="{password}" WHERE id="{user_id}"')
        return 'Your password was successfully restored.'

    @staticmethod
    @app.route('/new_password/<token>')
    def new_password(token) -> str:
        """Check if the token in the email sent to the user
        hasn't expired and if it's valid. If it is, a template
        for restoring a password will be rendered."""
        if Token.check_token(token) is False:
            return 'The link is either wrong or expired.'
        else:
            return render_template('email_pages/restore_password_letter.html', token=token)

    def _create_email(self) -> Message:
        """Construct the email for restring password."""
        verification_message = Message('Restore your password', recipients=[self.email_address])
        verification_message.html = '<a href="' + self._build_url() + '">' + self._build_url() + '</a>'
        return verification_message

    def _build_url(self) -> str:
        """Build a url leading to a new_password() function."""
        return url_for('new_password', token=self.token.create_token(self.user_id), _external=True)

    def _get_email_by_login(self, login: str) -> Union[str, None]:
        """Get user's email from given login."""
        return self.database.get_information(f'SELECT email FROM users WHERE login="{login}"',
                                             default=(None,))[0]

    def _check_if_email_confirmed(self) -> Union[tuple, bool]:
        """Check if user have confirmed his email before sending making
        him able to restore his password."""
        return self.database.get_information(f'SELECT email FROM users WHERE email="'
                                             f'{self.email_address}" AND status="1"', False)
