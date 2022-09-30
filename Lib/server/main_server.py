from typing import Union, Any
from threading import Thread
from json import dumps, JSONEncoder

from flask import render_template, request, url_for, redirect, Response, abort, jsonify
from flask_login import login_required, logout_user
from flask import session

from Lib.server.app_core import app, login_manager, users
from Lib.server.processes import RegistrationHandler, LogInHandler, PrivatePage, get_user
from Lib.server.utils import UsersObserver
from Lib.server.posts import FullyFeaturedPost

# Things that need fixing
#   User can have two personal page at once by just copy-pasting the link of his page
#   or logging in as a different person. He might break system for himself in some
#   cases
#
#
# Load personal page
#
# Add different pages and features for users and admins
#
# Post features:
#   Add curse-comment ban system
#   Add preferences system based on posts tags
#
# Add getters and setters instead of changing arguments directly

temp = {}  # a very bad solution, should solve this resend email problem somehow else
Thread(target=UsersObserver().check_unconfirmed_users).start()  # tracks users conditions


@app.route('/testing_page')
def rc():
    return render_template('testing.html')


class Encoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        return o.__dict__


@app.route('/onloading_test')
def req(count: int):
    post_amount = count*2
    data = {post_amount+1: FullyFeaturedPost(1),
            post_amount+1: FullyFeaturedPost(2)}
    return dumps(data, cls=Encoder)


@login_manager.user_loader
def load_user(user_id: str):
    current_user = users.get(session.get('login'))
    if int(user_id) == current_user:
        return get_user()
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


@app.route('/')
def clear_session():
    session.clear()
    abort(404)


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


def log_in():
    log_in_handler = LogInHandler()
    log_in_handler.log_user()
    responses = {1: render_template('log_in_page.html', errors='Wrong credentials'),
                 2: render_template('log_in_page.html', already_logged_in=True, logged_as=session.get('login'),
                                    name=log_in_handler.login),
                 3: redirect(url_for('personal_page')),
                 4: redirect('/admin/')}
    return responses.get(log_in_handler.status.value)


@app.route('/log_in_anyways/<login>')
@login_required
def log_in_anyways(login: str) -> Response:
    log_in_handler = LogInHandler()
    log_in_handler.force_log_in(login)
    if log_in_handler.status.value == 4:
        return redirect('/admin/')
    else:
        return redirect(url_for('personal_page'))


@app.route('/log_in_page', methods=['GET', 'POST'])
def log_in_page() -> Union[Response, str]:
    if request.method == 'GET':
        return render_template('log_in_page.html')
    else:
        return log_in()


@app.route('/personal_page', methods=['GET', 'POST'])
@login_required(session)
def personal_page():
    """try:
        already_logged_in = session['entries']
    except KeyError:
        already_logged_in = False
    if request.method == 'GET' and not already_logged_in:
        session['entries'] = True
        return render_template('private_page.html', login=app_core.user.login, post_settings=PrivatePage)
    elif already_logged_in is True:
        return redirect(url_for('log_in_page'))"""
    #  the code in the comment can track if the user already had a page opened and
    #  prevent him from opening a new one but it is not implemented for the reason that it will
    #  also not let anyone reload their private page.
    if request.method == 'GET':
        return render_template('main_page.html', login=get_user().get_login,
                               all_subbed_to_posts=PrivatePage().get_latest_post)


@app.route('/view/')
def view_post():
    post = FullyFeaturedPost(int(request.args.to_dict().get('post_id')))
    return render_template('post_page.html', post=post)


@app.route('/log_out')
@login_required(session)
def log_out():
    logout_user()
    return render_template('log_in_page.html')


app.run('0.0.0.0', port=4000, debug=True)
