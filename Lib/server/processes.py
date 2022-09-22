from flask import request, render_template, url_for, session
from flask_login import login_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadTimeSignature
from typing import Union
from enum import Enum
from datetime import datetime
from Lib.server.app_core import app, user
from Lib.server.managers import Manager
from Lib.server.database import DataBase


class RegistrationState(Enum):
    """Represents possible conditions of registration process"""
    LoginAlreadyExists = 0
    FieldsNotFilled = 1
    CredentialsFine = 2
    SuccessfullyCreated = 3


class LogInState(Enum):
    """Represents possible conditions of the process of logging in"""
    WrongCredentials = 0
    FieldsNotFilled = 1
    CredentialsFine = 2
    UserAlreadyLoggedIn = 3


class LogInHandler(Manager):
    """Class for conducting the logging in process"""
    _error_messages = {0: 'Wrong credentials', 1: 'You must fill all the fields', 3: True}

    def __init__(self) -> None:
        super(LogInHandler, self).__init__()
        self.status = None
        self.login = None

    @staticmethod
    def force_log_in(login: str) -> None:
        """Log in a user without doing any verification.
        Used to re-login user if he already has an active session"""
        session.pop(user.login)
        user.__init__(login)
        login_user(user)
        session[login] = login

    def log_user(self) -> tuple:
        """General function that launches all the processes of logging in
        :returns: tuple of enum LogInState class and None/string"""
        self.login = request.form.get('login')
        log_in_state = self._check_properties()
        if log_in_state == LogInState.CredentialsFine:
            return self._add_to_session(), None
        else:
            return log_in_state, self._error_messages.get(log_in_state.value)

    def _add_to_session(self):
        """Update the user object,
        log it in so it can pass through @login_required and add it to session.
        :returns: enum LogInState class"""
        user.__init__(self.login)
        login_user(user)
        session[self.login] = self.login
        return LogInState.CredentialsFine

    def _check_properties(self) -> LogInState:
        """Check if all the user-given data is alright.
        :returns: enum LogInState class"""
        if self.login == '':
            return LogInState.FieldsNotFilled
        elif self._find_user() == LogInState.WrongCredentials or self._check_password() is False:
            return LogInState.WrongCredentials
        elif self._check_if_user_logged_in() is not True:
            return LogInState.UserAlreadyLoggedIn
        else:
            return LogInState.CredentialsFine

    @staticmethod
    def _check_if_user_logged_in() -> bool:
        """Check whether the user logged in already.
        :returns: True if user is not logged in yet, False if he is."""
        if user.login not in session:
            return True
        else:
            return False

    def _find_user(self) -> LogInState:
        """Check if the user wth given login exist.
        :returns: enum LogInState class"""
        if not self.database.get_information(f"SELECT login FROM users WHERE login='{self.login}'"):
            return LogInState.WrongCredentials
        else:
            return LogInState.CredentialsFine

    def _check_password(self) -> bool:
        """Check if password hash stored in database matches the user-provided password.
        :returns: True if it matches, False if it does not"""
        password_state = check_password_hash(self.database.get_information(f"SELECT PASSWORD FROM users WHERE "
                                                                           f"login='{self.login}'")[0],
                                             request.form.get('password'))
        return password_state


class RegistrationHandler(Manager):
    """Class for conducting the registration process."""
    def __init__(self) -> None:
        super().__init__()
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
            self.error_messages = "Account with this name already exists. Please give your account a different name."
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
    def check_token(cls, token: str, expiration=1800) -> bool:
        # in development (there is no way for a user whose link is expired to activate his account)
        # accounts of users, who did not confirm their accounts in an hour should be deleted
        """Check if a token is right and has not expired yet."""
        try:
            user_id_credentials = cls.serializer.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'],
                                                       max_age=expiration)
            DataBase().update(f'''UPDATE users SET is_activated="1" WHERE id="{user_id_credentials}"''')
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
        verification_message.html = render_template('confirmation_letter.html',
                                                    confirm_url=self._build_confirmation_url())
        return verification_message

    def _build_confirmation_url(self) -> str:
        """Build a url for a confirm_email() function."""
        return url_for('confirm_email', token=self.token.create_token(self.user_id), _external=True)

    def _get_by_login(self) -> int:
        """Get user id from login."""
        return self.database.get_information(f"SELECT id FROM users WHERE login='{self.login}'")[0]
