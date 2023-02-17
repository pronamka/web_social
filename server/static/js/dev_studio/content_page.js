function buildPosts(post_dict){
    for (var i=0, l=post_dict.length; i<l; i++){
        var post = post_dict[i];
        const post_id = post['post_id'];
        insertHTML('#my_posts', buildHTML(post));
        $(`#delete-post-button-${post_id}`).on('click',  ()=>{
            deletePostDialog(post_id);
        })

        $(`#toggle-preview-button-${post_id}`).on('click', ()=>{
            togglePreview(post_id);
        })
    }
}

function togglePreview(post_id){
    path = `/static/upload_folder/`
    const elem = document.getElementById(`post-iframe-${post_id}`)
    var current_state = elem.getAttribute('preview_state')

    if(current_state=='preview'){
        elem.setAttribute('src', path+`articles/${post_id}.pdf`)
        elem.setAttribute('preview_state', 'article')
    }
    else{
        elem.setAttribute('src', path+`previews/${post_id}.jpeg`)
        elem.setAttribute('preview_state', 'preview')
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
    path = `/static/upload_folder/previews/${post['post_id']}.jpeg`
    html = `<div class="content-post-container">
                <iframe src="${path}" class='post-iframe' preview_state='preview' id='post-iframe-${post['post_id']}'></iframe>
                <div class='content-post-info'>
                <button id='toggle-preview-button-${post['post_id']}' class='toggle-preview-button' title='Toggle preview'>
                    <i class="fa-solid fa-layer-group"></i>
                </button>
                    <h3 class='content-post-title'>${post['title']}</h3>
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
                    <div class='post-actions-wrapper'>
                        <h3 class='post-action-label'>Post Actions</h3>
                        <button class='modify-properties-button'title="This feature is currently unavailable." disabled>
                            Change properties
                        </button>
                        <button class='delete-post-button' id='delete-post-button-${post['post_id']}'>
                            Delete
                        </button>
                    </div>
                </div>
            </div>`;
    return html
}

function deletePostDialog(post_id){
    document.getElementById('delete-post-dialog-delete-post-button').addEventListener(
        'onclick', ()=>{deletePost(post_id)})

    document.getElementById('delete-post-dialog').showModal()
}

function deletePost(post_id){
    user_password = document.getElementById('delete-article-user-password-input').value
    sendRequest('POST', '/delete_post/', {'post_id': post_id, 'password': user_password}).then(resp=>{
        if (resp == 'SUCCESSFUL'){
            alert('Deleted Successfully')
            document.getElementById('delete-post-dialog').close()
        }
        else{
            alert('Something went wrong!')
        }
    })
}


function loadContentPage(){
    sendRequest('POST', '/load_info/', content_page).then(resp => {
        content = JSON.parse(resp)
        content_page['posts_loaded'] += 2
        buildPosts(content['latest_posts'])
    })
}


//information needed to for loading posts on the content tab
const content_page = {'page': 'content', 'posts_loaded': 0, 'posts_required': 2, 'post_type': 2}

const local_post_loading_function = loadContentPage
