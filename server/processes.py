from typing import Union, Any, Callable, Optional
from enum import Enum
from datetime import datetime, timedelta
from json import dumps, JSONEncoder
from abc import ABC, abstractmethod
from functools import wraps

from flask import request, render_template, url_for, session, abort
from flask_login import login_user
from flask_mail import Mail, Message

from werkzeug.security import generate_password_hash, check_password_hash

from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadTimeSignature

from server.app_core import app, users
from server.database import DataBase
from server.posts import AdminPostRegistry, UserPostRegistry, \
    FullyFeaturedPost, CommentsRegistry
from server.user import UserFactory, Viewer, Author, Admin, UserRole
from server.managers import Manager
from server.search_engine import search_post


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
            elif not current_session.get('login'):
                return app.login_manager.unauthorized()

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


def get_user() -> Union[Viewer, Author, Admin]:
    """Get the user object that corresponds with the client machine."""
    return users.get(session.get('login'))


def search_for(query: str, required_amount: int = 5, start_with=0):
    """General function to search for posts and get information
    about them."""
    post_ids = [i.get('post_id') for i in search_post(query, limit=required_amount + start_with)[start_with:]]
    res = UserPostRegistry.get_posts_from_ids(post_ids)
    return dumps(res, cls=Encoder)


def write_comment(post_id: str, comment_text: str, is_reply: int = None) -> None:
    """Add a comment to a certain post.
    :param post_id: the id of the post under which a comment was left.
    :param comment_text: the text of the comment.
    :param is_reply: defines if the comment is a reply to another comment (it
    equals to 0 if it is not or to an id of another comment, if it is)."""
    # May be will be added as a method to any class
    # that represents a post or manager.
    data_package = (post_id, str(get_user().get_user_id), comment_text,
                    datetime.now().strftime("%A, %d. %B %Y %H:%M"), is_reply)
    DataBase(access_level=2).create(f'INSERT INTO comments(post_id, user_id, comment, date, is_reply) '
                                    f'VALUES(?, ?, ?, ?, ?);', data=data_package)


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


def author_required(func: Callable):
    """Check if the user that is trying to commit
    a certain action is an author."""

    def wrapper(self, *args):
        if get_user().get_role == UserRole.Viewer:
            return 0
        else:
            return func(self, *args)

    return wrapper


class InformationGetter:
    """Class for formalizing and getting information
    for loading content for pages (usually called by js on client)"""

    def __init__(self, properties: dict, **kwargs):
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
        self.protocols = {'subscribers': self.get_subscriber_amount,
                          'commentaries_made': ...,
                          'commentaries_received': self.amount_of_commentaries_received_on_post,
                          'post_amount': self.amount_of_posts,
                          'latest_posts': self.get_latest_posts,
                          'dated_posts': self.get_dated_posts,
                          'latest_comments': self.get_latest_comments_on_post,
                          'latest_comments_dev': self.get_latest_comments_of_users_posts}

    def get_full_data(self) -> dict:
        """Get all the data that was specified
        when initializing the InformationGetter."""
        data = {}
        for i in self.properties.keys():
            if (result := self.get_information(i)) != 0 and self.properties.get(i) == 'amount':
                data[i] = len(result)
            else:
                data[i] = result
        return data

    def get_information(self, method: str) -> Union[tuple, list, int]:
        """Get information, if it's covered in protocols.
        :param method: a string defining which information
            is needed (a key to a dictionary with arguments)"""
        return self.protocols.get(method)()

    def get_subscriber_amount(self):
        return self.user.SubscriptionManager.get_followers

    def get_latest_comments_on_post(self) -> tuple[FullyFeaturedPost]:
        post_id, amount, start_with = self.parameters.get('post_id', 0), \
                                      self.parameters.get('comments_required', 1), \
                                      self.parameters.get('comments_loaded', 0)
        return CommentsRegistry(post_id).get_latest_comments(amount, start_with)

    def get_latest_comments_of_users_posts(self):
        amount, start_with = self.parameters.get('comments_required'), \
                             self.parameters.get('comments_loaded')
        return self.user.PostManager.get_latest(amount, start_with, 'comments')

    def get_latest_posts(self) -> Union[int, tuple[FullyFeaturedPost]]:
        amount, start_with, of_user = self.parameters.get('posts_required', 1), \
                                      self.parameters.get('posts_loaded', 0), \
                                      self.parameters.get('of_user', True)
        if of_user and self.user.get_role == UserRole.Viewer:
            return 0
        elif of_user:
            return self.user.PostManager.get_latest(amount, start_with, 'posts')
        else:
            return UserPostRegistry.get_posts(amount, start_with)

    def amount_of_commentaries_made(self, *args):
        ...

    @author_required
    def amount_of_commentaries_received_on_post(self):
        return self.user.PostManager.get_comments_amount(self.parameters.get('post_id'))

    @author_required
    def amount_of_posts(self):
        return self.user.PostManager.get_post_amount()

    def get_dated_posts(self):
        dates_got = self.parameters.get('dates_loaded', 0)
        today = datetime.today()
        required_date = (today - timedelta(dates_got)).strftime('%Y-%m-%d')
        follows = self.user.SubscriptionManager.get_follows
        post_manager = UserPostRegistry()
        posts = post_manager.get_subscription_posts(required_date, follows)
        while not posts and required_date > '2022-09-15':  # 2022-09-15 is the date
            # of first post ever created. If the date goes below that, there is no need
            # to look for new posts, as there are none of them.
            dates_got += 1
            required_date = (today - timedelta(dates_got)).strftime('%Y-%m-%d')
            posts = post_manager.get_subscription_posts(required_date, follows)
        return posts, required_date, dates_got


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
            'view_post_page': {'latest_comments': 'object'},
            'hub': {'latest_posts': 'object',
                    'commentaries_received': 'amount',
                    'post_amount': 'object',
                    'subscribers': 'amount'},
            'content': {'latest_posts': 'object'},
            'comment_section': {'latest_comments_dev': 'object'}}
        data = InformationGetter(protocols.get(params.get('page')),
                                 parameters=params).get_full_data()
        return dumps(data, cls=Encoder)

    @staticmethod
    @app.route('/admin_get_posts', methods=['GET', 'POST'])
    @admin_required
    def admin_get_posts() -> str:
        data = {}
        posts_loaded, posts_required = request.json.values()
        for i in enumerate(AdminPostRegistry.get_posts(posts_required, posts_loaded)):
            data[i[0]] = i[1]
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
        query = f"INSERT INTO users (login, password, email, registration_date) VALUES (?, ?, ?, ?);"
        self.database.create(query, data=user_data)

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
        return self.database.get_information(f"SELECT id FROM users WHERE email="
                                             f"'{self.email_address}'", default=(None,))[0]


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
            DataBase(access_level=3).update(f'''UPDATE users SET status="1" WHERE id="{user_id}"''')
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
