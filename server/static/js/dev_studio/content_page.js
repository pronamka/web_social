function buildPosts(post_dict){
    for (var i=0, l=Object.keys(post_dict).length-1; i<=l; i++){
        post = buildHTML(post_dict[i]);
        insertHTML('#my_posts', post);
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
    html = `<div class="content-post-container">
                <iframe src="${path}" class='post-iframe'></iframe>
                <div class='content-post-info'>
                    <h3>${post['title']}</h3>
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
                        <button onclick="deletePostDialog(${post['post_id']})" class='delete-post-button'>
                            Delete
                        </button>
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
