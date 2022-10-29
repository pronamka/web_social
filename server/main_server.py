from typing import Union
from threading import Thread

from flask import render_template, request, url_for, redirect, Response, abort
from flask_login import login_required, logout_user
from flask import session

from server.app_core import app, login_manager, users
from server.processes import RegistrationHandler, LogInHandler, get_user
from server.utils import UsersObserver, FileManager
from server.posts import FullyFeaturedPost
from server.user import UserFactory

# Things that need fixing:
#   1)User can have two personal page at once by just copy-pasting the link of his page
#   or logging in as a different person. He might break system for himself in some
#   cases.
#
#   2) On subscription page posts are not displayed properly
#      (if no one of made a post in 24 hours then it will just stop loading posts),
#      it should be made so posts are loaded until the users screen is filled,
#      and he has to scroll to see more
#
# Load new pages:
#   Add at least a little bit of new styles to display the posts flow in the right order.
#
# Add different pages and features for users and admins.
#
# Add a search system.
#
# Add a way to comment and subscribe.
#
# Add likes, views,
#
# Add session expiry system.
#
# Load developer studio page:
#   Write a function to give the client information to display hub
#   Add content to different fields such as content, translations, monetization, commentaries etc.
#   Finally add a way to post and comment
#
#
# Post features:
#   1)Add curse-comment ban system.
#   2)Add preferences system based on posts tags.
#
# Add getters and setters instead of changing arguments directly.

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
def subscribed_to_videos():
    return render_template('personal_pages/subscriptions_page.html')


@app.route('/view_post/')
def view_post():
    post = FullyFeaturedPost(int(request.args.to_dict().get('post_id')))
    return render_template('personal_pages/post_page.html', post=post)


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
    user = get_user()
    FileManager(file, user.get_user_id).save()
    new_user = UserFactory.create_and_update(user.get_user_id)
    users[get_user().get_login] = new_user  # get_user in dictionary key can't be replaced with created user
    # variable because get_user would return a different object, as new user was created.
    return redirect(url_for('dev_studio'))


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
    print(1+1)
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
