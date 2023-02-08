const request_url = '/load_info/';

var extension_counter = -1;

var settings = {'page': 'main_user_page', 'posts_loaded': 0, 'posts_required': 8,
'of_user': 0}

document.addEventListener('DOMContentLoaded', getPosts());

function sendRequest(method, url, body) {
    const headers = {'Content-Type': 'application/json'}
    console.log(body)
    return fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: headers}).then(response => {
        return response.text()
    })
}

function getPosts(){
    sendRequest('POST', request_url, settings).then(resp => {
        posts_dict = JSON.parse(resp);
        settings['posts_loaded'] += settings['posts_required']
        settings['posts_required'] = 4
        console.log(posts_dict)
        buildPosts(posts_dict['latest_posts']);
    })
}
function buildPosts(post_dict){
    for (var i=0, l=Object.keys(post_dict).length; i<=l; i++){
        try{
            post = buildHTML(post_dict[i]);
            addPost(post);
        }
        catch(error){
            console.log(error);
        }
    }
}
function buildHTML(post){
    path = `/static/upload_folder/articles/${post['post_id']}.pdf`
    html = `<object class="table_cell">
            <iframe class="preview" src=${path} id="post_preview ${post['post_id']}"></iframe>
            <div class="post-short-information">
                <div class='title-and-avatar-wrapper'>
                    <img class="author-avatar" src="static/${post['author_avatar']}">
                    <p class="post-name">
                        <a href="/view_post/?post_id=${post['post_id']}" class="post-link" id="post ${post['post_id']}">${post['title']}</a>
                    </p>
                </div>
                <p class="author-name">by ${post['author']}</p>
            </div>
            </object>`
            ;
    return html
}

function addPost(html) {
    const tab = document.getElementById('post_flow');
    var template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    tab.appendChild(template.content);
    return template.content.firstChild;
}

