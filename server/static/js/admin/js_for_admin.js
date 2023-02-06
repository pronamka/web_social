// function now() and throttle() (that used here for 
// sending request properly (to avoid sending to many at)
// once) are taken from https://github.com/jashkenas/underscore.git


const request_url = '/admin_get_posts/'
var posts = {}
var extension_amount = 0

document.addEventListener('DOMContentLoaded', getPosts(2), {once: true});


function sendRequest(method, url, body) {
    const headers = {'Content-Type': 'application/json'}
    return fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: headers}).then(response => {
        return response.text()
    })
}

function getPosts(amount, with_reduced_offset=false){
    if (with_reduced_offset == true){
        extension_amount -= 1
    }
    sendRequest('POST', request_url, 
    {'posts_loaded': extension_amount, 'posts_required': amount}).then(resp => {
        post_json = JSON.parse(resp)
        extension_amount += amount
        buildPosts(post_json);
    })
}


function buildPosts(post_dict){
    for (var i=0; i<post_dict.length; i++){
        buildHTML(post_dict[i])
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
    path = `/static/upload_folder/articles/${post['post_id']}.pdf`
    html = `<div class="content-post-container" id='content-post-container-${post['post_id']}'>
                <iframe src="${path}" class='post-iframe'></iframe>
                <div class='content-post-info'>
                    <h3>${post['title']}</h3>
                    <p>${post['made_ago_str']}</p>
                    <div class='content-post-info-grid'>
                        <p class='post-info-description'>Title</p><div class="post-info-info">${post['title'] || ""}</div>
                        <p class='post-info-description'>Author</p><div class="post-info-info">${post['author'] || ""}</div>
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
                    <div class='post-actions-wrapper'>
                        <h3 class='post-action-label'>Post Actions</h3>
                        <button id='verify-post-button-${post['post_id']}' class='verify-post-button'>Verify</button>
                        <button id='examine-post-button-${post['post_id']}' class='examine-post-button'>Examine</button>
                    </div>
            </div>`;
    insertHTML('#post-table', html)
    $(`#verify-post-button-${post['post_id']}`).on('click', ()=>{
        console.log(post['post_id'])
        verifyPost(post['post_id'])
    })
    $(`#examine-post-button-${post['post_id']}`).on('click', ()=>{
        window.location.href=`/admin/examine_post/?post_id=${post['post_id']}`
    })
}

function verifyPost(post_id){
    console.log('fired')
    sendRequest('POST', '/admin/verify_post/', {'post_id': post_id}).then(resp => {
        document.querySelector(`#content-post-container-${post_id}`).remove()
        getPosts(1, true)
    })
}

with_avatar = false

