
function getPosts(){
    sendRequest('POST', request_url, settings).then(resp => {
        const posts_dict = JSON.parse(resp)['latest_posts'];
        settings['posts_loaded'] += posts_dict.length
        settings['posts_required'] = 4
        console.log(posts_dict)
        buildPosts(posts_dict);
    })
}


function buildPosts(post_dict){
    for (var i=0, l=post_dict.length; i<l; i++){
        insertHTML('#post_flow', buildHTML(post_dict[i]));
    }
}


function buildHTML(post){
    path = `/static/upload_folder/previews/${post['post_id']}.jpeg`
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

const request_url = '/load_info/';

var settings = {'page': 'main_user_page', 'posts_loaded': 0, 'posts_required': 8,
'of_user': 0}

document.addEventListener('DOMContentLoaded', getPosts);