const nav_tabs = document.querySelectorAll('[data-tab-value]');
const tabs_content = document.querySelectorAll('[data-tab-info]');
const action_protocols = {'hub': {'/inf_for_hub': null}, 
                        'content': {'call': loadContentPage, 'called': 0}, 
                        'analitics': {'/analitics': null},
                        'commentaries': {'/commentaries': 0}, 
                        'translations': {'/trananslations': 0},
                        };
const content_page = {'page': 'content', 'posts_loaded': 0, 'posts_required': 2, 'post_type': 'FullyFeaturedPost'}
const btn_upload_files = document.querySelector('btn-upload-files');

document.addEventListener('DOMContentLoaded', loadHub());


function sendRequest(method, url, body) {
    const headers = {'Content-Type': 'application/json'}
    return fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: headers}).then(response => {
        return response.text();
    })
}

function loadHub(){
    sendRequest('POST', '/load_info/', {'page': 'hub'}).then(resp => {
        content = JSON.parse(resp)
        console.log(content)
        if (content['latest_posts'] != 0){
            title=content['latest_posts']['0']['title'];
            path = '/static/upload_folder/'+title
            html = `<div class="table_cell">
                <iframe width="400" height="500" src="`+ path+`"></iframe>
                <p>`+title+`</p>
            </div>`;
        }
        else {
            html = `<div class="table_cell">
                        <img width="191" height="264" src="/static/images/no-posts-yet.jpg">
                        <p>You have not made any publications yet.
                        Click the button below to start!</p>
                        <button onclick="showUploadDialog();" id="btn-open-upload-dialog">
                        Add a post</button>
                    </div>`;
        }
        insertHTML('#last_post', html);
        console.log(content);
        subscribers = content['subscribers'];
        post_amount = content['post_amount'];
        comment_amount = content['commentaries_received'];
        html = `<p>You have `+ subscribers+`<p>
                <div class="ln-sep"></div>
                <h2>Short statistics:<h2>
                <p>You made`+ post_amount+` publications,
                and recieved `+ comment_amount+` comments<p>
                <a href="#analitics">Full statistics</a>`;
        insertHTML('#short_analitics', html);
    })
}
function loadContentPage(){
    sendRequest('POST', '/load_info/', content_page).then(resp => {
        content = JSON.parse(resp)
        console.log(content)
        content_page['posts_loaded'] += 2
        buildPosts(content['latest_posts'])
    })
}
current_position = 250
window.addEventListener("scroll", function(event) {
    var top = this.scrollY
    if (current_position < top){
        current_position += 1000
        loadContentPage();
    } 
}, false);

class Hub{
    constructor(content_dict){
        this.latest_posts = content_dict['latest_posts']
        this.commentaries_received = content_dict['commentaries_received']
        this.subscribers = content_dict['subscribers']
        this.post_amount = content_dict['post_amount']
    }
    
}

class Post{
    constructor(post_dict){
        this.author = post_dict['author'];
        this.comment_registry = post_dict['comment_registry'];
        this.creation_date = post_dict['creation_date'];
        this.post_id = post_dict['post_id'];
        this.post_title = post_dict['title'];
    }
    get allValues(){
        return (this.author, this.comment_registry, this.creation_date,
            this.post_id, this.post_title);
    }
    get comments(){
        if (this.comment_registry['comments'].length == 0){
            return ''
        }
        else{
            return this.comment_registry['comments']
        }
    }
    get author_login(){
        return this.author
    }
    get title(){
        return this.post_title
    }
}

function buildPosts(post_dict){
    for (var i=0, l=Object.keys(post_dict).length; i<=l; i++){
        var current_post = new Post(post_dict[i])
        current_post.allValues;
        if (current_post.comments == ''){
            print('in');
            comments = '<ul><li>No comments yet</li></ul>';
        }
        else{
            comments = buildComments(current_post.comments);
        }
        title = current_post.title;
        author = current_post.author_login;
        path = '/static/upload_folder/'+title;
        post = buildHTML(path, author, title, comments);
        addPost(post);
        }
    }
function buildHTML(path, author, title, comments){
    html = `<div class="table_cell">
            <iframe width="400" height="500" src="`+ path+`"></iframe>
            <details class="post_data" open>
                <summary>Post information</summary>
                <ul>
                <li>Title: `+title+`</li>
                <li>Author: `+author+`</li>
                <li><details>
                    <summary>Comment Registry</summary>`+comments+
                `</details></li>
                </ul>
            </details>
        </div>`;
    return html
}

function buildComments(comment_section){
    comments = '';
    for (var j=1, ln=Object.keys(comment_section).length; j<=ln; j++){
        if (Object.keys(comment_section).length > 0){
            comments = comments +  `<ul><details>
                <summary>Comment id: `+comment_section[j]['comment_id']+`</summary>
                <li class="comment_info">Comment author: `+comment_section[j]['author']+`</li>
                <li class="comment_info">Comment text: `+comment_section[j]['text']+`</li>
            </details></ul>`
        }
    }
    return comments
}

function addPost(html) {
    const tab = document.getElementById('my_posts');
    var template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    tab.appendChild(template.content);
    return template.content.firstChild;
}

function insertHTML(direction, html) {
    const tab = document.querySelector(direction);
    var template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    tab.appendChild(template.content);
    return template.content.firstChild;
}
function showUploadDialog () {
    const upload_dialog = document.querySelector('#dialog-upload-file');
    upload_dialog.showModal()
}

nav_tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const direction = document.querySelector(tab.dataset.tabValue);
        tabs_content.forEach(tabInfo => {
            tabInfo.classList.remove('active');
        })
        const a = direction['id']
        if (action_protocols[a]['called'] == 0){
            action_protocols[a]['call']()
        }
        direction.classList.add('active');
    })
})
