
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
        insertNode('#post_flow', buildHTML(post_dict[i]));
    }
}


function buildHTML(post){
    const path = stringConstants.previewFilePath.format(post['post_id'])

    const post_template = getTemplate('#post-preview-frame-main-page')
    const post_iframe = post_template.querySelector('iframe')
    const view_post_link = post_template.querySelector('a')

    post_iframe.setAttribute('src', path)

    post_template.querySelector('img').setAttribute('src', `static/${post['author_avatar']}`)
    post_template.querySelector('.author-name').innerText = `by ${post['author']}`
    
    view_post_link.setAttribute('href', `/view_post/?post_id=${post['post_id']}`)
    view_post_link.setAttribute('id', `view-post-link-post-${post['post_id']}`)
    view_post_link.innerText = post['title']

    post_template.removeAttribute('id')
    
    return post_template
}

const request_url = '/load_info/';

var settings = {'page': 'main_user_page', 'posts_loaded': 0, 'posts_required': 8,
'of_user': 0}

document.addEventListener('DOMContentLoaded', getPosts);