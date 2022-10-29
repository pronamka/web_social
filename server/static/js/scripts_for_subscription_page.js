const request_url = '/load_info/';

var settings = {'page': 'subscription_page', 'dates_loaded': 0}

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
        posts_dict = JSON.parse(resp);
        settings['dates_loaded'] += posts_dict['dated_posts'][2] +1
        buildPosts(posts_dict['dated_posts']);
    })
}
function buildPosts(post_dict){
    posts = post_dict[0]
    date = post_dict[1]
    if (posts.length > 0){
        addHTML('<h3>'+date+'</h3>')
        for (var i=0, l=Object.keys(posts).length; i<=l; i++){
            try{
                
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
        addHTML('<div class="ln-dates-sep"></div>')
        if (posts.length < 5) {
            getPosts();
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
