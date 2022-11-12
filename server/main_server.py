from typing import Union
from threading import Thread

from flask import render_template, request, url_for, redirect, Response, session
from flask_login import logout_user

from server.app_core import app, login_manager, users
from server.processes import RegistrationHandler, LogInHandler, RestorePasswordNotificationSender, \
    get_user, write_comment, admin_required, login_required
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
# Add a window to show progress when uploading a file.
#
# Add events system for handling registration, log in and other processes.
#
# Expand the search system(post tags, interests etc.)
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
#   Sort comments in dev studio by: latest; Made on specific post; seen/verified/liked/replied
#   (by author) already.
#   Add content to fields such as commentaries, analytics, translations, monetization etc.
#
#
#
# Post features:
#   1)Add curse-comment ban system.
#   2)Add preferences system based on posts tags.
#

Thread(target=UsersObserver().check_unconfirmed_users).start()  # tracks users conditions


def handle_registration(login: str, password: str, email: str) -> dict:
    """General function for conducting the process of registration."""
    registration_handler = RegistrationHandler(login, password, email)
    registration_handler.create_new_user()
    if registration_handler.status.value == 3:
        return {'status': 300, 'redirect': url_for('confirm_email_page', login=registration_handler.login)}
    else:
        return {'status': 406, 'error': registration_handler.error_messages}


@app.route('/confirm_email_page/<login>')
def confirm_email_page(login: str) -> str:
    """View for displaying a page, where a user can
    request resending an email-confirmation message."""
    return render_template('email_pages/confirm_email_page.html', login=login)


@app.route('/resend_confirmation_email/<login>')
def resend_confirmation_email(login: str) -> Response:
    """View for resending an email to confirm email address"""
    RegistrationHandler.resend_email(login)
    return Response(status=200)


@app.route('/registration_page')
def registration_page() -> Union[Response, str]:
    """View for displaying the registration page and
    starting the process of registration."""
    return render_template('registration_page.html')


@app.route('/register/', methods=['POST'])
def register():
    login, password, email = request.json.values()
    return handle_registration(login, password, email)


@app.route('/log_in/', methods=['GET', 'POST'])
def log_in():
    """General function for starting the process of logging in."""
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
    """View for removing the current user session, and starting a
    new one (log in with another account)."""
    log_in_handler = LogInHandler()
    log_in_handler.force_log_in()
    if log_in_handler.status.value == 5:
        return {'status': 300, 'response': '/admin/'}
    else:
        return {'status': 300, 'response': url_for('personal_page')}


@app.route('/log_in_page', methods=['GET', 'POST'])
def log_in_page() -> Union[Response, str]:
    """Open log in page"""
    return render_template('log_in_page.html')


@app.route('/admin/examine_post/', methods=['GET', 'POST'],
           endpoint='examine_post')
@admin_required
def examine_post():
    """Open a page where a post is displayed, so an admin
    can examine it and ban/verify."""
    post_id = int(request.args.to_dict().get('post_id'))
    post = FullyFeaturedPost(post_id)
    return render_template('admin/examine_post.html', post=post)


@app.route('/admin/ban_post/', methods=['GET', 'POST'], endpoint='admin_ban_post')
@admin_required
def admin_ban_post():
    """A view for banning a post for admins."""
    post_id, problem_description = request.json.values()
    assert problem_description, 'You did not provide problem description.'
    get_user().ban_post(post_id, problem_description, app)
    return {'status': 'successful'}


@app.route('/admin/verify_post/', methods=['GET', 'POST'], endpoint='admin_verify_post')
@admin_required
def admin_verify_post():
    """A view for verifying a post for admins."""
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
    #  prevent him from opening a new one, but it is not implemented for the reason that it will
    #  also not let anyone reload their private page.
    if request.method == 'GET':
        return render_template('personal_pages/main_page.html')


@app.route('/subscriptions/')
@login_required(session)
def subscribed_to_posts():
    """Open a page where the posts of the people user is subscribed to
    are going to be displayed. The posts themselves are loaded later
    by js fetch request."""
    return render_template('personal_pages/subscriptions_page.html')


@app.route('/view_post/')
@login_required(session)
def view_post():
    """Open a page designed for displaying a post."""
    post = FullyFeaturedPost(int(request.args.to_dict().get('post_id')))
    return render_template('personal_pages/post_page.html', post=post,
                           current_user_follows=get_user().SubscriptionManager.get_follows)


@app.route('/comment/', methods=['GET', 'POST'])
@login_required(session)
def add_comment():
    """General function for starting the process of
    adding a comment."""
    #  There is no way to delete comment
    #  neither for comments authors nor for post authors,
    #  but this feature is coming soon.
    data = request.json
    post_id, comment_text, is_reply = data.get('post_id'), data.get('comment_text'), \
                                      data.get('is_reply', None)
    write_comment(post_id, comment_text, is_reply)
    return Response(status=200)


@app.route('/change_subscriptions/', methods=['GET', 'POST'])
@login_required(session)
def change_subscriptions():
    """Subscribe or unsubscribe from a certain user.
    The action (subscribe/unsubscribe) and the user, to which
    the action is going to be applied, are both passed as a body
    of a post request."""
    author_id, action = map(int, request.json.values())
    manager = get_user().SubscriptionManager
    protocols = {0: manager.unfollow, 1: manager.follow}
    protocols.get(action)(author_id)
    return Response(status=200)


# WARNING: this will be decorated with @login_required, when most of the
# features of development_studio are done. It isn't for know to make the
# testing easier.
@app.route('/development_studio/')
def dev_studio():
    """Load the page of the development studio."""
    return render_template('personal_pages/post_developer_pages/dev_studio.html')


@app.route('/upload_file/', methods=['POST'])
def upload_file():
    """General function for starting the process
    of receiving a file from a user and saving it to the disk."""
    file = request.files['file']
    response = FileManager(file, get_user().get_user_id).save()
    if isinstance(response, str):
        return Response(response, status=406)
    check_role()
    return Response('Successfully saved the file. It is '
                    'going to be able for others to see '
                    'after it is verified by our experts.', status=200)


def check_role() -> None:
    """This is a part of the process of uploading file.
    Check the user's role, and if it's Viewer (it's user's first posts),
    then change it to Author."""
    user = get_user()
    if user.get_role == UserRole.Viewer:
        new_user = UserFactory.update_role(user.get_user_id)
        users[user.get_login] = new_user


@app.route('/restore_password/', methods=['GET', 'POST'])
def restore_password():
    """General function for starting the process of restoring
    password. The only thing that should be passed as a body
    of a request is an email, to which a link to restore password
    will be sent."""
    # WARNING: changing password by login may be deprecated soon
    # to prevent anybody from sending restore-password links
    # to any account they know login of. It does not do
    # anything bad, but it might be confusing, so we are
    # considering all the pros and cons and our decision
    # will come soon.
    email_address, login = request.json.values()
    status = RestorePasswordNotificationSender(email_address=email_address,
                                               login=login).send_email()
    return status


@app.route('/search/', methods=['GET', 'POST'])
def search():
    """Search for the posts that are in any way connected to the
    query given. All information that specifies what data is required
    (query itself, result_required and start_with) are passed
    as a body of the request."""
    query, results_required, start_with = request.json.values()
    data = search_for(query, results_required, start_with)
    return data


@app.route('/search_page/', methods=['GET', 'POST'])
def search_page():
    """Just renders page where search results will be displayed.
    This view does not do any searching. It passes the
    search query as a request argument and also embeds it to
    some values in the page. The search will be done later, when
    the js on the loaded page requests /search/."""
    query = request.args.to_dict().get('query')
    return render_template('personal_pages/search_results_page.html',
                           search_query=query)


@app.route('/log_out')
@login_required(session)
def log_out():
    """Log user out (he will no longer pass through @login_required),
    clean the session."""
    logout_user()
    users.pop(session.pop('login')), session.pop('id')
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
