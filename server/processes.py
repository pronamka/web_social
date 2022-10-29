from typing import Union, Any, Optional, Literal, Callable
from enum import Enum
from datetime import datetime, timedelta
from json import dumps, JSONEncoder

from flask import request, render_template, url_for, session
from flask_login import login_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadTimeSignature

from server.app_core import app, users
from server.database import DataBase
from server.posts import PostForDisplay, AdminPostRegistry, UserPostRegistry, \
    FullyFeaturedPost
from server.user import UserFactory, Viewer, Author, Admin, UserRole
from server.managers import Manager, BasicManager


def get_user() -> [Viewer, Author, Admin]:
    """Get the user object that corresponds with the client machine."""
    return users.get(session.get('login'))


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
    def default(self, o: Any) -> Any:
        return o.__dict__


def author_required(func: Callable):
    def wrapper(self, *args):
        if get_user().get_role == UserRole.Viewer:
            return 0
        else:
            return func(self, *args)
    return wrapper


class InformationGetter:
    """Class for formalizing and getting information
    for loading pages of development studio."""
    def __init__(self, properties: dict, **kwargs):
        """Initialize InformationGetter.
        :param properties: dictionary with all
            typed of information needed.
        :param kwargs: dictionary with some special
            information for loading exact values
            (e.g. how many posts were already loaded
            and which too load now etc.) Not always required."""
        self.properties = properties
        self.parameters = kwargs.get('parameters')
        self.user = get_user()
        self.protocols = {'subscribers': (self.get_subscriber_amount,),
                          'commentaries_made': ...,
                          'commentaries_received': (self.amount_of_commentaries_received_on_post,
                                                    (self.parameters.get('post_id'),)),
                          'post_amount': (self.amount_of_posts,),
                          'latest_posts': (self.get_latest_posts,
                                           (self.parameters.get('posts_need', 1),
                                            self.parameters.get('posts_got', 0)))}

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

    def get_information(self, method: Literal['subscribers', 'commentaries_made',
                                              'commentaries_received', 'post_amount', 'latest_posts']
                        ) -> Union[tuple, list, int]:
        """Get information, if it's covered in protocols.
        :param method: a string defining which information
            is needed. It is a key to the protocols dictionary.
            All possible options described in the type hint."""
        if (func := self.protocols.get(method)[0]) and len(self.protocols.get(method)) > 1:
            # noinspection PyArgumentList
            return func(*self.protocols.get(method)[1])
        else:
            return func()

    def get_subscriber_amount(self, *args):
        return self.user.SubscriptionManager.get_followers

    @author_required
    def get_latest_posts(self, amount: int = 1, start_with: int = 0) \
            -> tuple[FullyFeaturedPost]:
        return self.user.PostManager.get_latest_posts(amount, start_with)

    def amount_of_commentaries_made(self, *args):
        ...

    @author_required
    def amount_of_commentaries_received_on_post(self, post_id: int):
        return self.user.PostManager.get_comments_amount(post_id)

    @author_required
    def amount_of_posts(self, *args):
        return self.user.PostManager.get_post_amount()


class PostLoader:
    """Class that stores views for loading more posts.
    It's methods get called automatically by js on client side.
    The methods overlap each other, so our crew is developing
    a method to combine them."""

    # those methods are not safe because they can be called
    # by any user, to get info it they are not supposed to get
    # some kind of verification or password/token system should be implemented

    @staticmethod
    @app.route('/load_info/', methods=['GET', 'POST'])
    def load_info():
        """Get whatever info you want specified in protocols
        (info and other parameters should be passed as request arguments)"""
        params = request.json
        protocols = {'hub': {'latest_posts': 'object',
                             'commentaries_received': 'amount',
                             'post_amount': 'object',
                             'subscribers': 'amount'},
                     'content': {'latest_posts': 'object'}}
        data = InformationGetter(protocols.get(params.get('page')),
                                 parameters=params).get_full_data()
        return dumps(data, cls=Encoder)

    @staticmethod
    @app.route('/extend_posts', methods=['GET', 'POST'])
    def extend_posts() -> str:
        #  the js on the client side calls this when posts need to be loaded.
        data = {}
        post_amount = 4
        count = request.json
        for i in enumerate(UserPostRegistry.get_posts(post_amount, int(count) * post_amount)):
            data[i[0]] = i[1]
        return dumps(data, cls=Encoder)

    @staticmethod
    @app.route('/extend_sub_posts', methods=['GET', 'POST'])
    def extend_sub_posts():
        data = {}
        req_date = (datetime.today() - timedelta(int(request.json))).strftime('%Y-%m-%d')
        print(req_date)
        for i in enumerate(UserPostRegistry.get_sub_posts(req_date,
                                                          get_user().SubscriptionManager.get_follows)):
            data[i[0]] = i[1]
        data['date'] = req_date
        return dumps(data, cls=Encoder)

    @staticmethod
    @app.route('/admin_get_posts', methods=['GET', 'POST'])
    def admin_get_posts() -> str:
        #  the js on the client side calls this when posts need to be loaded
        #  for admin.
        # post verification system should be added
        data = {}
        post_amount = 2
        count = request.json
        for i in enumerate(AdminPostRegistry.get_posts(post_amount, int(count) * 2)):
            data[i[0]] = i[1]
        print(data)
        return dumps(data, cls=Encoder)


class PrivatePage:
    def __init__(self) -> None:
        if get_user().get_role.value == 1:
            self.latest_posts = PostRegistry.get_others_latest_posts()
        elif get_user().get_role.value == 2:
            self.latest_posts, self.my_latest_posts = PostRegistry.get_data()

    @property
    def get_latest_post(self) -> list:
        return self.latest_posts


class PostRegistry(BasicManager):
    """An object for getting information needed to display a post"""

    @classmethod
    def get_data(cls) -> tuple:
        """Get both latest post of users who the current user is subscribed to
                and his own latest posts."""
        return cls.get_others_latest_posts(), cls.get_my_latest_posts()

    @classmethod
    def get_others_latest_posts(cls) -> [str, list]:
        """Get latest post of users who the current user is subscribed to."""
        follows = get_user().SubscriptionManager.get_follows
        if follows:
            post_ids = cls.database.get_all_singles(f'SELECT MAX(post_id) FROM posts WHERE user_id IN '
                                                    f'({", ".join(str(i) for i in follows)})')
            return list(map(PostForDisplay, post_ids))
        else:
            return 'None of people who you follow have made a post.'

    @classmethod
    def get_my_latest_posts(cls) -> list:
        """Get latest post of a current user"""
        return get_user().PostManager.get_latest_posts(5)


class LogInHandler(Manager):
    """Class for conducting the logging in process"""
    _actions = {1: UserFactory.create_viewer, 2: UserFactory.create_author, 3: UserFactory.create_admin}

    def __init__(self) -> None:
        super(LogInHandler, self).__init__()
        self.status = None
        self.login = None

    def force_log_in(self, login: str) -> None:
        """Log in a user without doing any verification.
        Used to re-login user if he already has an active session"""
        users.pop(session.get('login'))
        self._log_in(login)

    def log_user(self) -> tuple:
        """General function that launches all the processes of logging in"""
        self.login = request.form.get('login')
        self._check_properties()
        if self.status.value >= 4:
            self._log_in(self.login)
        return self.status

    def _log_in(self, login: str) -> LogInState:
        """Update the user object,
        log it in so it can pass through @login_required and add it to session."""
        info = self._find_by_login(login)
        # noinspection PyArgumentList
        users[login] = self._actions.get(info[1])(info[0])
        self._add_to_session(login)
        return LogInState.CredentialsFine

    def _add_to_session(self, login: str) -> None:
        login_user(users.get(login))
        session['login'] = login
        session['id'] = str(get_user().get_user_id)
        self._check_if_admin()

    def _find_by_login(self, login: str) -> tuple[int, int]:
        return self.database.get_information(f'SELECT id, role FROM users WHERE login="{login}"')

    def _check_if_admin(self):
        if get_user().get_role == UserRole.Admin:
            self.status = LogInState.AdminUser

    def _check_properties(self) -> None:
        """Check if all the user-given data is alright."""
        if self._find_user() == LogInState.WrongCredentials or self._check_password() is False:
            self.status = LogInState.WrongCredentials
        elif self.database.get_information(f'SELECT status FROM users WHERE '
                                           f'login="{self.login}"')[0] != 1:
            self.status = LogInState.EmailNotConfirmed
        elif not session.get('login') != self.login:
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
                                   request.form.get('password'))


class RegistrationHandler(Manager):
    """Class for conducting the registration process."""

    #  WARNING: users can create different accounts with one email.
    #  This is only to make testing easier and should be fixed before deployment

    def __init__(self) -> None:
        super().__init__(2)
        self.login: str = request.form.get('login')
        self.password: str = request.form.get('password')
        self.email: str = request.form.get('email')
        self.status: RegistrationState = self._check_properties()
        self.error_messages = None

    def resend_email(self) -> None:
        """Resend email. If you want to send email to a specific user do not use this function
        as it will send the message to the email address of a RegistrationHandler instance"""
        email_confirmation_handler = EmailConfirmationHandler(self.login, self.email)
        email_confirmation_handler.send_confirmation_email()

    def create_new_user(self) -> None:
        """General function that launches all the processes."""
        if self._check_status():
            self._create_in_db()
            email_confirmation_handler = EmailConfirmationHandler(self.login, self.email)
            email_confirmation_handler.send_confirmation_email()
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
    database = DataBase(access_level=3)

    @classmethod
    def create_token(cls, user_id: int) -> str:
        """Create a token."""
        return cls.serializer.dumps(user_id, app.config['SECURITY_PASSWORD_SALT'])

    @classmethod
    def check_token(cls, token: str, expiration=1800) -> bool:
        """Check if a token is right and has not expired yet."""
        try:
            user_id_credentials = cls.serializer.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'],
                                                       max_age=expiration)
            cls.database.update(f'''UPDATE users SET status="1" WHERE id="{user_id_credentials}"''')
            return True
        except BadTimeSignature:
            return False


class EmailConfirmationHandler(Manager):
    """Class for conducting the process of email confirmation."""

    def __init__(self, login: str, email: str) -> None:
        super().__init__()
        self.email_manager = Mail(app)
        self.login = login
        self.email = email
        self.user_id = self._get_by_login()
        self.token = Token()

    @app.route('/send_email/<login>/<email>')
    def send_confirmation_email(self) -> str:
        """Send the email message to it's recipients."""
        email_message = self._create_email()
        self.email_manager.send(email_message)
        return render_template('registration_page.html')

    @staticmethod
    @app.route('/confirm_email/<token>')
    def confirm_email(token: str) -> str:
        """Check the token in the user's email message."""
        status = Token.check_token(token)
        if status is not True:
            return 'The link is either wrong or expired.'
        else:
            return 'Your account is confirmed, thanks. You can now close this page.'

    def _create_email(self) -> Message:
        """Build the the actual email message (html)"""
        verification_message = Message('Confirm your email address', recipients=[self.email])
        verification_message.html = render_template('email_pages/confirmation_letter.html',
                                                    confirm_url=self._build_confirmation_url())
        return verification_message

    def _build_confirmation_url(self) -> str:
        """Build a url for a confirm_email() function."""
        return url_for('confirm_email', token=self.token.create_token(self.user_id), _external=True)

    def _get_by_login(self) -> int:
        """Get user id from login."""
        return self.database.get_information(f"SELECT id FROM users WHERE login='{self.login}'")[0]
