const nav_tabs = document.querySelectorAll('[data-tab-value]');
const tabs_content = document.querySelectorAll('[data-tab-info]');
const action_protocols = {'hub': {'call': loadHub, 'called': 1}, 
                        'content': {'call': loadContentPage, 'called': 0}, 
                        'analitics': {'call': loadContentPage, 'called': 0},
                        'commentaries': {'call': loadCommentsPage, 'called': 0}, 
                        'translations': {'/trananslations': 0},
                        };
const content_page = {'page': 'content', 'posts_loaded': 0, 'posts_required': 2, 'post_type': 'FullyFeaturedPost'}
const comments_page = {'page': 'comment_section', 'comments_loaded': 0, 'comments_required': 10}
const btn_upload_files = document.querySelector('btn-upload-files');

document.addEventListener('DOMContentLoaded', loadHub());


function sendRequest(method, url, body, multipart=false) {
    const headers = {'Content-Type': 'application/json'}
    if (multipart == true){
        return fetch(url, {
            method: method,
            headers: headers,
            body: body}).then(response => {
            return response.text();
        })
    }
    else{
        return fetch(url, {
            method: method,
            body: JSON.stringify(body),
            headers: headers}).then(response => {
            return response.text();
        })
    }
}

function loadHub(){
    sendRequest('POST', '/load_info/', {'page': 'hub'}).then(resp => {
        content = JSON.parse(resp)
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
        content_page['posts_loaded'] += 2
        buildPosts(content['latest_posts'])
    })
}

function loadCommentsPage(){
    sendRequest('POST', '/load_info/', comments_page).then(resp=>{
        console.log(resp)
        comments = JSON.parse(resp)
        console.log(comments)
        comments_page['comments_loaded'] += comments_page['comments_required']
        insertHTML('#latest_comments_table', buildComments(comments['latest_comments_dev']))
    })
}

class Comment{
    constructor(comment_info){
        this.comment_id_val = comment_info['comment_id']
        this.author_val = comment_info['author']
        this.date_val = comment_info['date']
        this.text_val = comment_info['text']
        this.post_id_val = comment_info['post_id']
    }
    get comment_id(){
        return this.comment_id_val
    }
    get author(){
        return this.author_val
    }
    get date(){
        return this.date_val
    }
    get text(){
        return this.text_val
    }
    get post_id(){
        return this.post_id_val
    }

}
function buildComments(comments_array){
    comments = '';
    if (comments_array.length == 0){
        return 'No comments.'
    }
    for (var i=0, l=Object.keys(comments_array).length-1; i<=l; i++){
        const comment = new Comment(comments_array[i])
        console.log(comment)
        var cur_id = comment.comment_id
        comments += `<tr>
        <td id="author ${cur_id}">${comment.author}</td>
        <td id="date ${cur_id}">${comment.date}</td>
        <td id="text ${cur_id}">${comment.text}</td>
        <td id="post_id ${cur_id}">${comment.post_id}</td>
        <td id="reply ${cur_id}"><button onclick="reply([`+comment.comment_id+`, '`+comment.author+`', '`+comment.text+`', `+comment.post_id+`])">Reply</button></td>
        </tr>`
    }
    return comments
}
function reply(comment){
    var reply_dialog = document.querySelector('#reply_dialog')
    reply_dialog.innerHTML = `<h2>Reply to<h2>
    <p>${comment[1]}'s comment</p>
    <p>${comment[2]}<p>
        <input type="text" placeholder="Your reply" id="inp-comment-reply ${comment[0]}">
        <button placeholder="Reply" onclick="sendReply([`+comment[0]+`, '`+comment[1]+`', '`+comment[2]+`', `+comment[3]+`])"></button>`
    reply_dialog.showModal()
}

function sendReply(comment){
    sendRequest('POST', '/comment/', {'post_id': comment[3] ,
    'reply_text': comment[2], 'is_reply': comment[0]})
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
    for (var i=0, l=Object.keys(post_dict).length-1; i<=l; i++){
        var current_post = new Post(post_dict[i])
        current_post.allValues;
        title = current_post.title;
        author = current_post.author_login;
        path = '/static/upload_folder/'+title;
        post = buildHTML(path, author, title);
        addPost(post);
        }
    }
function buildHTML(path, author, title){
    html = `<div class="table_cell">
            <iframe width="400" height="500" src="`+ path+`"></iframe>
            <details class="post_data" open>
                <summary>Post information</summary>
                <ul>
                <li>Title: `+title+`</li>
                <li>Author: `+author+`</li>
                </ul>
            </details>
        </div>`;
    return html
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

function uploadArticle(){
    const file_data = document.getElementById('inp-file-content').files[0]
    const file_article = new FormData()
    file_article.append('file', file_data)
    file_article.append('filename', file_data['name'])
    fetch('/upload_file/', {method: 'POST', body: file_article, 
    headers: {'Accept': 'application/json'}}).then(response=>response.text()).then(resp=>{
        console.log(resp)
        alert(resp)
    })
}

nav_tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const direction = document.querySelector(tab.dataset.tabValue);
        tabs_content.forEach(tabInfo => {
            tabInfo.classList.remove('active');
        })
        const a = direction['id']
        console.log()
        if (action_protocols[a]['called'] == 0){
            action_protocols[a]['call']()
        }
        direction.classList.add('active');
    })
})
