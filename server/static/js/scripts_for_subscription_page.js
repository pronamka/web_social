const request_url = '/load_info/';

var settings = {'page': 'subscription_page', 'posts_required': 5, 'posts_loaded': 0,
'last_date': 0, 'post_type': 2}

document.addEventListener('DOMContentLoaded', getPosts());

function sendRequest(method, url, body) {
    const headers = {'Content-Type': 'application/json'}
    return fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: headers}).then(response => {
        return response.text()
    })
}

function getPosts(){
    sendRequest('POST', request_url, settings).then(resp => {
        const posts_dict = JSON.parse(resp);
        settings['posts_loaded'] += settings['posts_required']
        buildPosts(posts_dict['dated_posts']);
    })
}

function buildTagsRepresentation(tags){
    var repr = ''
    for (i = 0; i<tags.length; i++){
        repr += `<li>${tags[i]}</li>`
    }
    return repr
}

function buildPosts(posts){
    if (posts.length > 0){
        for (var i=0, l=Object.keys(posts).length; i<l; i++){
            try{
                if (settings['last_date'] != posts[i]['creation_date']){
                    addHTML(`<h3 class="date-date-separator">${posts[i]['creation_date']}</h3>`)
                    addHTML('<div class="ln-dates-sep"></div>')
                    settings['last_date'] = posts[i]['creation_date']
                }
                post = buildHTML(posts[i]);
                addHTML(post);
            }
            catch(error){
                console.log(error);
            }
        }
    }
}

function buildHTML(post){
    path = `/static/upload_folder/articles/${post['post_id']}.pdf`
    html = `<object class="table_cell">
                <iframe class="preview" src="${path}"></iframe>
                <div class='all-post-info'>
                    <img class="author-avatar" src="/static/${post['author_avatar']}">
                    <div class="post-short-information">
                        <div class="title-and-author">
                            <p class="post-name">
                                <a href="/view_post/?post_id=${post['post_id']}">${post['title']}</a>
                            </p>
                            <p class="person_name">${post['author']}</p>
                        </div>
                        <p class="made-ago">${post['made_ago_str']}</p>
                    </div>
                    <div class='post-tags'>
                        <details>
                            <summary>Post tags</summary>
                            <ul>
                                ${buildTagsRepresentation(post['tags_flattened'])}
                            </ul>
                        </details>
                    </div>
                </div>
            </object>`
            ;
    return html
}

function addHTML(html) {
    const tab = document.getElementById('post_flow');
    var template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    tab.appendChild(template.content);
    return template.content.firstChild;
}

