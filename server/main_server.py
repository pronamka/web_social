from typing import Union, Callable
from threading import Thread
from functools import wraps

from flask import render_template, request, url_for, redirect, Response, abort
from flask_login import login_required, logout_user
from flask import session

from server.app_core import app, login_manager, users
from server.processes import RegistrationHandler, LogInHandler, EmailBanMessageSender, \
    get_user, verify_post, write_comment
from server.utils import UsersObserver, FileManager
from server.posts import FullyFeaturedPost
from server.user import UserFactory, UserRole

# Things that need fixing:
#   1)User can have two personal page at once by just copy-pasting the link of his page
#   or logging in as a different person. He might break system for himself in some
#   cases.
#
#   2)Loading post with specific date on subscription page requires accessing
#   database numerous times to find anything. It should only require accessing
#   it one time, and looking for the first entry instead.
#
# Add a way for users to restore passwords if forgotten.
#
# Add events system for handling registration, log in and other processes.
#
# Add different pages and features for users and admins.
#
# Add a search system.
#
# Add a way to comment and subscribe.
#
# Add likes, views.
#
# Add session expiry system.
#
# Add a way to copyright posts.
#
# Add a way to redact posts for admins.
#
# Load developer studio page:
#   Write a function to give the client information to display hub
#   Add a way to comment
#   Add content to fields such as commentaries, analytics, translations, monetization etc.
#
#
# Post features:
#   1)Add curse-comment ban system.
#   2)Add preferences system based on posts tags.
#

temp = {}  # a very bad solution, should solve this resend email problem somehow else
Thread(target=UsersObserver().check_unconfirmed_users).start()  # tracks users conditions


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
        return render_template('email_pages/confirm_email_page.html')
    else:
        temp.get(login).resend_email()
        temp.pop(login)
        return render_template('email_pages/confirm_email_page.html')


@app.route('/registration_page', methods=['GET', 'POST'])
def registration_page() -> Union[Response, str]:
    """This view will display the registration page
    and start registration process."""
    if request.method == 'GET':
        return render_template('registration_page.html')
    else:
        return register()


def log_in():
    session.clear()  # this here is only to make testing easier, should be deleted before deployment
    log_in_handler = LogInHandler()
    log_in_handler.log_user()
    responses = {1: render_template('log_in_page.html', errors='Wrong credentials.'),
                 2: render_template('log_in_page.html', already_logged_in=True,
                                    logged_as=session.get('login'),
                                    name=log_in_handler.login),
                 3: render_template('log_in_page.html', errors='You did not confirm your email.'),
                 4: redirect(url_for('personal_page')),
                 5: redirect('/admin/')}  # defines how the function should act,
    # depending on the log_in_handler status.
    return responses.get(log_in_handler.status.value)


@app.route('/log_in_anyways/<login>')
@login_required(session)
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


def admin_required(func: Callable):
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


@app.route('/admin/examine_post/', methods=['GET', 'POST'],
           endpoint='examine_post')
@admin_required
def examine_post():
    post_id = int(request.args.to_dict().get('post_id'))
    post = FullyFeaturedPost(post_id)
    return render_template('admin/examine_post.html', post=post)


@app.route('/admin/ban_post/', methods=['GET', 'POST'], endpoint='admin_ban_post')
@admin_required
def admin_ban_post():
    post_id, problem_description = request.json.values()
    assert problem_description, 'You did not provide problem description.'
    EmailBanMessageSender(post_id, problem_description).send_ban_notification()
    return {'status': 'successful'}


@app.route('/admin/verify_post/', methods=['GET', 'POST'], endpoint='admin_verify_post')
def admin_verify_post():
    post_id: int = request.json
    verify_post(post_id)
    return {'status': 'successful'}


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
        return render_template('personal_pages/main_page.html')


@app.route('/subscriptions/')
@login_required(session)
def subscribed_to_videos():
    return render_template('personal_pages/subscriptions_page.html')


@app.route('/view_post/')
@login_required(session)
def view_post():
    post = FullyFeaturedPost(int(request.args.to_dict().get('post_id')))
    return render_template('personal_pages/post_page.html', post=post)


@app.route('/comment/', methods=['GET', 'POST'])
@login_required(session)
def add_comment():
    post_id, comment_text = request.json.values()
    write_comment(post_id, comment_text)
    return 'a'


@app.route('/development_studio/')
def dev_studio():
    session['login'] = 'prona'  # this here is only to make the testing easier
    session['id'] = '2'
    users['prona'] = UserFactory.create_author(2)  # (so i don't have to clear session,
    # and log in again every time i want to load the page)
    return render_template('personal_pages/post_developer_pages/dev_studio.html')


@app.route('/upload_file/', methods=['GET', 'POST'])
def upload_file():
    file = request.files['file']
    FileManager(file, get_user().get_user_id).save()
    check_role()
    return redirect(url_for('dev_studio'))


def check_role() -> None:
    user = get_user()
    if user.get_role == UserRole.Viewer:
        new_user = UserFactory.create_and_update(user.get_user_id)
        users[user.get_login] = new_user


@app.route('/log_out')
@login_required(session)
def log_out():
    logout_user()
    session.pop('login')
    return redirect(url_for('log_in_page'))


@login_manager.user_loader
def load_user(user_id: str):
    """This function is the part of the logging in process.
    It is needed to define if user should be authorized."""
    current_user = users.get(session.get('login'))
    if int(user_id) == current_user:
        return get_user()
    else:
        return None


@app.route('/')
def clear_session():
    #  This is just to clear the session easier, as I can't log in
    #  if I restarted the server but never closed my browser window.
    #  This view is going to be removed when development is over.
    session.clear()
    abort(404)


app.run('0.0.0.0', port=4000, debug=True, use_debugger=True, use_reloader=True)
