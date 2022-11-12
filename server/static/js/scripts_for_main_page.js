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
            title = post_dict[i]['title'];
            author = post_dict[i]['author'];
            post_id = post_dict[i]['post_id'];
            path = '/static/upload_folder/'+title;
            post = buildHTML(path, author, title, post_id);
            addPost(post);
        }
        catch(error){
            console.log(error);
        }
    }
}
function buildHTML(path, author, title, post_id){
    html = `<object class="table_cell">
            <iframe width="300" height="500" class="preview" src="`+ path+`"></iframe>
            <div class="for_preview">
                <p class="post_name">
                <a href="/view_post/?post_id=${post_id}" id="post ${post_id}">`+ title+`</a>
                </p><br><p class="person_name">by `+ author+`</p>
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


current_position = 380
window.addEventListener("scroll", function(event) {
    var top = this.scrollY
    console.log(top, current_position)
    if (current_position < top){
        current_position += 620
        getPosts();
    } 
}, false);