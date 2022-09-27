from flask import render_template, request, url_for, redirect, Response
from flask_login import login_required
from flask import session
from typing import Union
from threading import Thread
from Lib.server import app_core
from Lib.server.app_core import app, login_manager
from Lib.server.processes import RegistrationHandler, LogInHandler, PrivatePage
from Lib.server.utils import UsersObserver

# Fix everything s oit works with new user system
#
#
# Load personal page
#   Add different pages and features for users and admins
#   Add curse-comment ban system
#   Add preferences system based on posts tags
# Add getters and setters instead of changing arguments directly

temp = {}  # a very bad solution, should solve this resend email problem somehow else
Thread(target=UsersObserver().check_unconfirmed_users).start()  # tracks users conditions


@login_manager.user_loader
def load_user(user_id: str):
    if int(user_id) == app_core.user.user_id:
        return app_core.user
    else:
        return None


def register() -> Union[Response, str]:
    registration_handler = RegistrationHandler()
    registration_handler.create_new_user()
    temp[registration_handler.login] = registration_handler
    return check_status(registration_handler.status, login=registration_handler.login,
                        errors=registration_handler.error_messages)


def check_status(status, **kwargs) -> Union[Response, str]:
    if status.value == 3:
        return redirect(url_for('confirm_email_page', login=kwargs.get('login')))
    else:
        return render_template('registration_page.html', errors=kwargs.get('errors'))


@app.route('/confirm_email_page/<login>', methods=['GET', 'POST'])
def confirm_email_page(login: str) -> str:
    if request.method == 'GET':
        return render_template('confirm_email_page.html')
    else:
        temp.get(login).resend_email()
        temp.pop(login)
        return render_template('confirm_email_page.html')


@app.route('/registration_page', methods=['GET', 'POST'])
def registration_page() -> Union[Response, str]:
    if request.method == 'GET':
        return render_template('registration_page.html')
    else:
        return register()


def log_in() -> Union[Response, str]:
    log_in_handler = LogInHandler()
    status = log_in_handler.log_user()
    if status[0].value == 2:
        return redirect(url_for('personal_page'))
    elif status[0].value == 3:
        return render_template('log_in_page.html', already_logged_in=True, name=session.get(app_core.user.login))
    else:
        return render_template('log_in_page.html', errors=status[1])


@app.route('/log_in_anyways/<login>', methods=['GET', 'POST'])
def log_in_anyways(login: str) -> Response:
    LogInHandler.force_log_in(login)
    return redirect(url_for('personal_page'))


@app.route('/log_in_page', methods=['GET', 'POST'])
def log_in_page() -> Union[Response, str]:
    if request.method == 'GET':
        return render_template('log_in_page.html')
    else:
        return log_in()


@app.route('/personal_page', methods=['GET', 'POST'])
@login_required
def personal_page():
    if request.method == 'GET':
        return render_template('private_page.html', login=app_core.user.login, post_settings=PrivatePage)


app.run('0.0.0.0', port=4000, debug=True)