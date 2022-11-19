const request_url = '/load_info/';

var settings = {'page': 'subscription_page', 'posts_required': 5, 'posts_loaded': 0,
'last_date': 0}

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
function buildPosts(posts){
    console.log(posts)
    if (posts.length > 0){
        for (var i=0, l=Object.keys(posts).length; i<=l; i++){
            try{
                if (settings['last_date'] != posts[i]['creation_date']){
                    addHTML(`<h3>${posts[i]['creation_date']}</h3>`)
                    addHTML('<div class="ln-dates-sep"></div>')
                    settings['last_date'] = posts[i]['creation_date']
                }
                title = posts[i]['title'];
                author = posts[i]['author'];
                post_id = posts[i]['post_id'];
                path = '/static/upload_folder/'+title;
                post = buildHTML(path, author, title, post_id);
                addHTML(post);
            }
            catch(error){
                console.log(error);
            }
        }
    }
}
function buildHTML(path, author, title, post_id){
    html = `<object class="table_cell">
            <iframe width="250" height="400" class="preview" src="`+ path+`"></iframe>
            <div class="for_preview">
                <p class="post_name">
                <a href="/view_post/?post_id=`+post_id+`">`+ title+`</a>
                </p><br><p class="person_name">by `+ author+`</p>
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

current_position = 250
window.addEventListener("scroll", function(event) {
    var top = this.scrollY
    if (current_position < top){
        current_position += 1000
        getPosts();
    } 
}, false);
