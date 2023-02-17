from typing import Union
from threading import Thread

from flask import render_template, request, url_for, redirect, Response, session
from flask_login import logout_user

from server.app_core import app, login_manager, users
from server.processes import RegistrationHandler, LogInHandler, RestorePasswordNotificationSender, \
    get_user, write_comment, admin_required, login_required, author_required
from server.utils import UsersObserver, ArticleManager, ImageManager
from server.posts import PostExtended, FullyFeaturedPost
from server.user import UserFactory, UserRole
from server.processes import search_for, check_password


# send a notification when post on a certain topic (tracked by a user) gets verified
# make session live even when user's browser window is closed
# replies should be deleted on cascade when the main comment is deleted or
# when the posts the comments are made on gets deleted

# add a way for users to delete their own posts and comments

# notifications on personal page? / your comments on personal page?

# Things that need fixing:
#   1)When calculating score by word appearances (while searching) only the last word in
#   the request is counted, so the result can be inaccurate.
#
# Add a system of priority when approving posts for admins (some posts will be top
# priority and examined as quick as possible, while other will have to wait in a queue)
#
# Add a window to show progress when uploading a file and registering.
#
# Add events system for handling registration, log in and other processes.
#
# Add a way to copyright posts.
#
# Add a way to redact posts for admins.
#
# Add a reliance system to indicate users whose posts and comments get banned often
#
# Add a channel page where users will be able to see the posts and information about
#  other user.
#
# Load developer studio page:
#   Sort comments in dev studio by: Made on specific post;
#   Add content to translations, monetization, copyright.
#
# Post features:
#   1)Add curse-comment ban system.


Thread(target=UsersObserver().check_unconfirmed_users).start()  # tracks users with unconfirmed email


def get_request_data(keys: dict, get_from: dict) -> list:
    data = []
    for i in keys.keys():
        data.append(get_from.get(i, keys.get(i)))
    return data


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
    """View for displaying the registration page."""
    return render_template('registration_page.html')


@app.route('/register/', methods=['POST'])
def register() -> dict:
    """Register a new user."""
    login, password, email = get_request_data({'login': None, 'password': None, 'email': None}, request.json)
    return handle_registration(login, password, email)


@app.route('/log_in/', methods=['GET', 'POST'])
def log_in() -> dict:
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
def log_in_anyways() -> dict:
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
def examine_post() -> str:
    """Open a page where a post is displayed, so an admin
    can examine it and ban/verify."""
    post_id = int(request.args.to_dict().get('post_id'))
    post = FullyFeaturedPost(post_id)
    return render_template('admin/examine_post.html', post=post)


@app.route('/admin/ban_post/', methods=['GET', 'POST'], endpoint='admin_ban_post')
@admin_required
def admin_ban_post() -> dict:
    """A view for banning a post for admins."""
    post_id, problem_description = request.json.values()
    assert problem_description, 'You did not provide problem description.'
    get_user().ban_post(post_id, problem_description, app)
    return {'status': 'successful'}


@app.route('/admin/verify_post/', methods=['GET', 'POST'], endpoint='admin_verify_post')
@admin_required
def admin_verify_post() -> dict:
    """A view for verifying a post for admins."""
    get_user().verify_post(request.json.get('post_id'), app)
    return {'status': 'successful'}


@app.route('/personal_page', methods=['GET', 'POST'])
@login_required(session)
def personal_page() -> str:
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
    return render_template('personal_pages/main_page.html')


@app.route('/subscriptions/')
@login_required(session)
def subscribed_to_posts() -> str:
    """Open a page where the posts of the people user is subscribed to
    are going to be displayed. The posts themselves are loaded later
    by js fetch request."""
    return render_template('personal_pages/subscriptions_page.html')


@app.route('/private_page/')
@login_required(session)
def private_page() -> str:
    return render_template('personal_pages/personal_page.html')


@app.route('/view_post/')
@login_required(session)
def view_post() -> str:
    """Open a page designed for displaying a post."""
    post_id = int(request.args.to_dict().get('post_id'))
    post = PostExtended(post_id, True, True)
    user = get_user()
    user.view_post(post_id)
    subscribed = 1 if post.get_author_id in user.SubscriptionManager.get_follows else 0
    return render_template('personal_pages/post_page.html', post=post, is_subscribed=subscribed,
                           liked=1 if user.check_if_liked(post_id)[0] else 0)


@app.route('/like_post/')
@login_required(session)
def like_post():
    post_id, new_status = get_request_data({'post_id': None, 'new_status': 1}, request.args.to_dict())
    get_user().change_like_status(post_id, new_status)
    return Response('SUCCESSFUL', status=200)


@app.route('/comment/', methods=['GET', 'POST'])
@login_required(session)
def add_comment() -> dict:
    """General function for starting the process of
    adding a comment."""
    data = request.json
    post_id, comment_text, is_reply = get_request_data({'post_id': None, 'comment_text': None,
                                                        'is_reply': 0}, data)
    if not comment_text:
        return {}
    return write_comment(post_id, comment_text, is_reply)


@app.route('/delete_comment/')
@login_required
def delete_comment():
    comment_id = int(request.args.to_dict().get('comment_id'))
    get_user().remove_comment(comment_id)
    return Response('SUCCESSFUL', status=200)


@app.route('/delete_post/', methods=['POST'])
def delete_post():
    post_id, password = get_request_data({'post_id': -1, 'password': '0'}, request.json)
    user = get_user()
    if not check_password(user.get_user_id, password):
        return Response('WRONG_CREDENTIALS', status=406)
    if user.get_role.value != 2:
        return Response('NO_PERMISSION', status=406)
    user.remove_post(int(post_id))
    return Response('SUCCESSFUL', status=200)


@app.route('/ban_comment/', methods=['POST'])
@author_required
def ban_comment() -> Response:
    """Ban a comment under a post. This can function requires for user to be an author."""
    comment_id, reason = request.json.values()
    status = get_user().author_ban_comment(app, comment_id, reason)
    if status:
        return Response(status=403)
    return Response(status=200)


@app.route('/mark_comment_as_seen/', methods=['POST'])
@author_required
def mark_comment_as_seen() -> Response:
    comment_id = request.json.get('comment_id')
    status = get_user().mark_comment_as_seen(comment_id)
    if status:
        return Response(status=403)
    return Response(status=200)


@app.route('/change_subscriptions/', methods=['GET', 'POST'])
@login_required(session)
def change_subscriptions() -> Response:
    """Subscribe or unsubscribe from a certain user.
    The action (subscribe/unsubscribe) and the user, to which
    the action is going to be applied, are both passed as a body
    of a post request."""
    author_id, action = map(int, request.json.values())
    manager = get_user().SubscriptionManager
    protocols = {0: manager.unsubscribe, 1: manager.subscribe}
    protocols.get(action)(author_id)
    return Response(status=200)


@app.route('/development_studio/')
@login_required(session)
def dev_studio() -> str:
    """Load the page of the development studio."""
    return render_template('personal_pages/post_developer_pages/dev_studio.html')


def check_role() -> None:
    """This is a part of the process of uploading a file.
    Check the user's role, and if it's Viewer (it's user's first posts),
    then change it to Author."""
    user = get_user()
    if user.get_role == UserRole.Viewer:
        new_user = UserFactory.update_role(user.get_user_id)
        users[user.get_login] = new_user


@app.route('/upload_file/', methods=['POST'])
def upload_file() -> Response:
    """General function for starting the process
    of receiving a file from a user and saving it to the disk."""
    try:
        file = request.files['article']
        preview = request.files['preview']
        tags = request.values.get('tags')
    except KeyError:
        return Response('Something went wrong.', status=400)
    if not file or not tags:
        return Response('NO_DATA', status=400)
    response = ArticleManager(file, preview, get_user().get_user_id, tags).save()
    if isinstance(response, str):
        return Response(response, status=406)
    check_role()
    return Response('Successfully saved the file. It is '
                    'going to be able for others to see '
                    'after it is verified by our experts.', status=200)


@app.route('/restore_password/', methods=['GET', 'POST'])
def restore_password() -> dict:
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


@app.route('/search/', methods=['POST'])
def search() -> dict:
    """Search for the posts that are in any way connected to the
    query given. All information that specifies what data is required
    (query itself, result_required and start_with) are passed
    as a body of the request."""
    params = get_request_data({'search_query': None, 'results_required': 5,
                               'results_received': 0, 'search_strictly': False}, request.json)
    data = search_for(*params)
    return data


@app.route('/search_page/', methods=['GET'])
@login_required(session)
def search_page() -> str:
    """Just renders the page where the search results will be displayed.
    This view does not do any searching. It passes the
    search query as a request argument and also embeds it to
    some values in the page. The search will be done later, when
    the js on the loaded page requests /search/."""
    query, search_strictly, add_to_search = get_request_data({'query': '', 'search_strictly': '',
                                                              'add_to_search': ''}, request.args.to_dict())
    if add_to_search:
        with open('testing/words.txt', mode='a+') as file:
            for i in query.split(' '):
                if i not in file.read().split():
                    file.write(i + '  ')
    return render_template('personal_pages/search_results_page.html',
                           search_query=query, search_strictly=search_strictly)


@app.route('/change_interests/', methods=['POST'])
@login_required(session)
def change_interests() -> Response:
    """Function for receiving and updating used interests."""
    interests = request.json.get('interests')
    if not interests:
        return Response('NO_DATA', 406)
    else:
        get_user().update_interests(interests)
        return Response('SUCCESSFUL', 200)


@app.route('/change_avatar/', methods=['POST'])
@login_required(session)
def change_avatar() -> Response:
    """Function for changing the user's avatar. Receives the new avatar as a form data
    in the body of the request."""
    file = request.files['file']
    user_id = get_user().get_user_id
    ImageManager(file, user_id).save()
    get_user().update_avatar()
    return Response('SUCCESSFUL', 200)


@app.route('/log_out')
@login_required(session)
def log_out() -> Response:
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


app.run(host='0.0.0.0', port=4000, debug=True, use_debugger=True, use_reloader=True)
