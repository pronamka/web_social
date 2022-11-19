from typing import Callable

from flask import Flask, session, abort
from flask_login import LoginManager
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy

from server.database import DataBase

app = Flask(__name__)
app.config['SECURITY_PASSWORD_SALT'] = 'salt'
app.config['SECRET_KEY'] = 'purple'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = ''
app.config['MAIL_DEFAULT_SENDER'] = ''
app.config['MAIL_PASSWORD'] = ''
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///web_social_v4.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

login_manager = LoginManager(app)
login_manager.session_protection = 'strong'

users = {}

db = SQLAlchemy(app)


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


class MyModelView(ModelView):
    @admin_required
    def is_accessible(self):
        return True

    def inaccessible_callback(self, name, **kwargs):
        return abort(404)


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String)
    password = db.Column(db.String)
    email = db.Column(db.String)
    registration_date = db.Column(db.String)
    followers = db.Column(db.String)
    follows = db.Column(db.String)
    status = db.Column(db.Integer)
    role = db.Column(db.Integer)


class Posts(db.Model):
    post_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String)
    date = db.Column(db.String)


class Comments(db.Model):
    comment_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comment = db.Column(db.String)
    date = db.Column(db.String)


admin = Admin(app, name='WebSocial', index_view=AdminView())
admin.add_view(MyModelView(Users, db.session))
admin.add_view(MyModelView(Posts, db.session))
admin.add_view(MyModelView(Comments, db.session))
