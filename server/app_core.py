from typing import Callable
from ast import literal_eval

from flask import Flask, session, abort
from flask_login import LoginManager
from flask_admin import Admin, AdminIndexView, expose
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from server.database import DataBase

app = Flask(__name__)
app.config['SECURITY_PASSWORD_SALT'] = 'salt'  # normal salt should be inserted here
app.config['SECRET_KEY'] = 'purple'  # need a better secret key
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True

with open('server_settings.txt', mode='r') as settings_file:
    mail_settings: dict = literal_eval(settings_file.read()).get('mail_settings')
    if not mail_settings.get('STATUS', 0):
        app.config['MAIL_USERNAME'] = mail_settings.get('MAIL_USERNAME')
        app.config['MAIL_DEFAULT_SENDER'] = mail_settings.get('MAIL_DEFAULT_SENDER')
        app.config['MAIL_PASSWORD'] = mail_settings.get('MAIL_PASSWORD')

login_manager = LoginManager(app)
login_manager.session_protection = 'strong'

users = {}


def admin_required(func: Callable):
    def wrapper(*args):
        role = DataBase().get_information(f'SELECT role FROM users WHERE '
                                          f'id="{users.get(session.get("login")).get_user_id}"')  # ignore that
        if role and role[0] == 3:
            return func(args[0])
        else:
            return abort(418)

    return wrapper


class AdminView(AdminIndexView):
    @expose('/')
    @admin_required
    def index(self):
        return super(AdminView, self).index()


admin = Admin(app, name='WebSocial', index_view=AdminView())


request_rate_limiter = Limiter(app=app, key_func=get_remote_address,
                               default_limits=['3 per second', '60 per minute'])
