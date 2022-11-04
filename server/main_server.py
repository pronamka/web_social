from typing import Union
from threading import Thread

from flask import render_template, request, url_for, redirect, Response, session
from flask_login import logout_user

from server.app_core import app, login_manager, users
from server.processes import RegistrationHandler, LogInHandler, RestorePasswordNotificationSender, \
    get_user, write_comment, admin_required, login_required, Encoder
from server.utils import UsersObserver, FileManager
from server.posts import FullyFeaturedPost
from server.user import UserFactory, UserRole
from server.processes import search_for


# Things that need fixing:
#   1)User can have two personal page at once by just copy-pasting the link of his page
#   or logging in as a different person. He might break system for himself in some
#   cases.
#
#   2)Loading post with specific date on subscription page requires accessing
#   database numerous times to find anything. It should only require accessing
#   it one time, and looking for the first entry instead.
#
# Add events system for handling registration, log in and other processes.
#
# Add a search system.
#
# Add likes, views.
#
# Add session expiry system.
#
# Add a way to copyright posts.
#
# Add a way to redact posts for admins.
#
# Add a channel page where users will be able to see the posts and information about
#  other user.
#
# Load developer studio page:
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


@app.route('/log_in/', methods=['GET', 'POST'])
def log_in():
    log_in_handler = LogInHandler()
    log_in_handler.log_user()
    responses = {1: {'status': 406, 'response': 'Not enough data'},
                 2: {'status': 409, 'response': 'Already logged in', 'logged_as': session.get('login')},
                 3: {'status': 412, 'response': 'Email not confirmed'},
                 4: {'status': 300, 'response': url_for('personal_page')},
                 5: {'status': 300, 'response': '/admin/'}}  # defines how the function should act,
    # depending on the log_in_handler status.
    current_response = responses.get(log_in_handler.status.value)
    return current_response


@app.route('/log_in_anyways/', methods=['POST'])
@login_required(session)
def log_in_anyways():
    log_in_handler = LogInHandler()
    log_in_handler.force_log_in()
    if log_in_handler.status.value == 5:
        return {'status': 300, 'response': '/admin/'}
    else:
        return {'status': 300, 'response': url_for('personal_page')}


@app.route('/log_in_page', methods=['GET', 'POST'])
def log_in_page() -> Union[Response, str]:
    return render_template('log_in_page.html')


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
    get_user().ban_post(post_id, problem_description, app)
    return {'status': 'successful'}


@app.route('/admin/verify_post/', methods=['GET', 'POST'], endpoint='admin_verify_post')
def admin_verify_post():
    get_user().verify_post(*request.json.values())
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
    return render_template('personal_pages/post_page.html', post=post,
                           current_user_follows=get_user().SubscriptionManager.get_follows)


@app.route('/comment/', methods=['GET', 'POST'])
@login_required(session)
def add_comment():
    post_id, comment_text = request.json.values()
    write_comment(post_id, comment_text)
    return Response(status=200)


@app.route('/change_subscriptions/', methods=['GET', 'POST'])
@login_required(session)
def change_subscriptions():
    author_id, action = map(int, request.json.values())
    manager = get_user().SubscriptionManager
    pro = {0: manager.unfollow, 1: manager.follow}
    pro.get(action)(author_id)
    return Response(status=200)


@app.route('/development_studio/')
def dev_studio():
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


@app.route('/restore_password/', methods=['GET', 'POST'])
def restore_password():
    email_address, login = request.json.values()
    status = RestorePasswordNotificationSender(email_address=email_address,
                                               login=login).send_email()
    return status


@app.route('/search/', methods=['GET', 'POST'])
def search():
    query = request.json.get('query')
    data = search_for(query)
    return data


@app.route('/search_page/', methods=['GET', 'POST'])
def search_page():
    query = request.args.to_dict().get('query')
    return render_template('personal_pages/search_results_page.html',
                           search_query=query)


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


app.run('0.0.0.0', port=4000, debug=True, use_debugger=True, use_reloader=True)
