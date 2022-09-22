from flask import Flask
from flask_login import LoginManager
from Lib.server.user import User

app = Flask(__name__)
app.config['SECURITY_PASSWORD_SALT'] = 'salt'
app.config['SECRET_KEY'] = 'secret_key'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'defender0508'
app.config['MAIL_DEFAULT_SENDER'] = 'defender0508@gmail.com'
app.config['MAIL_PASSWORD'] = 'dnqqunaesokbfrok'

login_manager = LoginManager(app)
login_manager.session_protection = 'strong'

user = User('0')
