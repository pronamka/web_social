const request_url = '/load_info/';

var settings = {'page': 'subscription_page', 'posts_required': 5, 'posts_loaded': 0,
'last_date': 0, 'post_type': 2}

document.addEventListener('DOMContentLoaded', getPosts());

function getPosts(){
    sendRequest('POST', request_url, settings).then(resp => {
        const posts_dict = JSON.parse(resp)['dated_posts'];
        settings['posts_loaded'] += posts_dict.length;
        buildPosts(posts_dict);
    })
}

function buildPosts(posts){
    if((settings['posts_loaded'] === 0) && (posts.length===0)){
        insertHTML('#post_flow', '<h3 class="no-subscriptions-info">You are not subscribed to anybody yet.</h3>')
        return false
    }
    if (posts.length > 0){
        for (var i=0, l=Object.keys(posts).length; i<l; i++){
            if (settings['last_date'] != posts[i]['creation_date']){
                insertHTML('#post_flow', `<h3 class="date-date-separator">${posts[i]['creation_date']}</h3>`)
                insertHTML('#post_flow', '<div class="ln-dates-sep"></div>')
                settings['last_date'] = posts[i]['creation_date']
            }
            insertHTML('#post_flow', buildHTML(posts[i]));
        }
    }
}

function buildPostTags(tags){
    html = ''
    for (var i=0; i<tags.length; i++){
        html+=`<li class='post-tag'>${tags[i]}</li>`
    }
    return html
}

function buildHTML(post){
    const path = stringConstants.previewFilePath.format(post['post_id'])

    const post_template = getTemplate('#post-preview-frame-subscriptions-page')
    post_template.querySelector('iframe').setAttribute('src', path)
    const view_post_link = post_template.querySelector('a')

    post_template.querySelector('.author-name').innerText = `by ${post['author']}`
    post_template.querySelector('.made-ago').innerText = post['made_ago_str']
    
    view_post_link.setAttribute('href', `/view_post/?post_id=${post['post_id']}`)
    view_post_link.innerText = post['title']

    post_template.removeAttribute('id')
    

    
    html = `<div class="content-post-container">
                <iframe src="${path}" class='post-iframe'></iframe>
                <div class='content-post-info'>
                    <h3><a href="/view_post/?post_id=${post['post_id']}">${post['title']}</a></h3>
                    <p>${post['made_ago_str']}</p>
                    <div class='content-post-info-grid'>
                        <p class='post-info'>Views</p><div class="post-info-number">${post['views_amount'] || 0}</div>
                        <p class='post-info'>Likes</p><div class="post-info-number">${post['like_amounts'] || 0}</div>
                        <p class='post-info'>Comments</p><div class="post-info-number">${post['comments_amount'] || 0}</div>
                    </div>
                    <div class='post-tags-wrapper'>
                        <details class='post-tags-details'>
                            <summary class='post-tags-summary'>
                                Post Tags
                            </summary>
                            <ul>
                                ${buildPostTags(post['tags_flattened'])}
                            </ul>
                        </details>
                    </div>
                </div>
            </div>`;
    return html
}