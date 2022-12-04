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
const comments_with_replies = {}
var article_upload_tags = {}
var chosen_tags_plain = {}

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
        comments = JSON.parse(resp)
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
function buildComments(comments_array, indent=0){
    comments = '';
    if (comments_array.length == 0){
        return 'No comments.'
    }
    for (var i=0, l=Object.keys(comments_array).length-1; i<=l; i++){
        const comment = new Comment(comments_array[i])
        var cur_id = comment.comment_id
        comments_with_replies[cur_id] = [0, 5]
        data_package = `[${comment.comment_id}, '${comment.author}', '${comment.text}', ${comment.post_id}]`
        comments += `<tr class="comments_table_row" title="Click to see replies." 
        onclick="loadReplies(${cur_id})" id="comment_row ${cur_id}" style="position: relative; left: ${indent};">
        <td>${comment.author}</td>
        <td>${comment.date}</td>
        <td>${comment.text}</td>
        <td>${comment.post_id}</td>
        <td><button onclick="reply(${data_package})">Reply</button></td>
        <td><button onclick="ban(${data_package})">Ban</button></td>
        </tr>`
    }
    return comments
}
function loadReplies(comment_id){
    var cur_comment = comments_with_replies[comment_id]
    console.log(cur_comment)
    sendRequest('POST', '/load_info/', {'page': 'comments', 
    'object_id': comment_id, 'comments_required': cur_comment[1], 
    'comments_loaded': cur_comment[0], 'object_type': 'reply'}).then(resp =>{
        comments_with_replies[comment_id][0] += cur_comment[1]
        const comments = buildComments(JSON.parse(resp)['latest_comments'], '50px').trim()
        const tab = document.getElementById('latest_comments_table');
        const after_element = document.getElementById(`comment_row ${comment_id}`)
        var template = document.createElement('template');
        template.innerHTML = comments;
        tab.insertBefore(template.content, after_element.nextSibling)
    }
    )
}
function reply(comment){
    var reply_dialog = document.querySelector('#reply_dialog')
    reply_dialog.innerHTML = `<h2>Reply to<h2>
    <p>${comment[1]}'s comment</p>
    <p>${comment[2]}<p>
        <input type="text" placeholder="Your reply" id="inp-comment-reply ${comment[0]}">
        <button id="send_reply_btn ${comment[0]}" placeholder="Reply" 
        onclick="sendReply([${comment[0]}, '${comment[1]}'
        , ${comment[3]}])">Send reply</button>`
    reply_dialog.showModal()
}

function ban(comment){
    var reply_dialog = document.querySelector('#reply_dialog')
    reply_dialog.innerHTML = `<h2>Ban<h2>
    <p>${comment[1]}'s comment</p>
    <p>${comment[2]}<p>
    <p>State a reason (optional):<p>
    <input type="text" placeholder="Reason" id="inp-comment-ban ${comment[0]}">
    <button id="ban_comment_btn ${comment[0]}" 
    onclick="sendBanRequest(${comment[0]})">Ban</button>`
    reply_dialog.showModal()
}
function sendBanRequest(comment_id){
    console.log(comment_id)
    var reason = document.getElementById(`inp-comment-ban ${comment_id}`).value
    console.log(reason)
    sendRequest('POST', '/ban_comment/', {'comment_id': comment_id, 
    'reason': reason}).then(resp=>{
        console.log(resp)
        document.querySelector('#reply_dialog').close()
    })
}

function sendReply(comment){
    const reply_text = document.getElementById(`inp-comment-reply ${comment[0]}`).value
    sendRequest('POST', '/comment/', {'post_id': comment[2] ,
    'comment_text': reply_text, 'is_reply': comment[0]}).then(resp=>{
        document.querySelector('#reply_dialog').close()
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
    file_article.append('tags', JSON.stringify(article_upload_tags))
    console.log(file_article)
    fetch('/upload_file/', {method: 'POST', body: file_article, 
    headers: {'Accept': 'application/json'}}).then(response=>response.text()).then(resp=>{
        console.log(resp)
        alert(resp)
    })
}

function getParent(key){
    console.log(key)
    var elem = document.getElementById(key)
    var child_of = elem.getAttribute('child_of')
    return child_of
}
function getFullInheritanceTree(key){
    var elem = document.getElementById(key)
    var child_of = elem.getAttribute('child_of')
    var tree = {}
    s = {}
    s[key] = {}
    if (child_of=="All interests"){
        return s
    }
    tree[child_of] = s
    while (true){
        var parent = getParent(child_of)
        if (parent == 'All interests'){
            return tree
        }
        var s = tree
        tree = {}
        tree[parent] = s
        child_of = parent
    }
}

function flatten(interest_tree_dict){
    var keys = Object.keys(interest_tree_dict)
    var result = {}
    for (var i=0, l=keys.length; i<l; i++){
        result[keys[i]] = {}
        if (interest_tree_dict[keys[i]].length != 0){
            result = Object.assign({}, result, flatten(interest_tree_dict[keys[i]]))
        }
    }
    return result
}
function searchAndInsert(interest_tree, user_tree){
    var interest = Object.keys(interest_tree)[0]
    chosen_tags_plain[interest] = {}
    if (interest in user_tree){
        user_tree[interest] = searchAndInsert(interest_tree[interest], user_tree[interest])
        return user_tree
    }
    else{
        var further_interests = interest_tree[interest]
        if (further_interests == null){
            further_interests = {}
        }
        user_tree[interest] = further_interests
        return user_tree
    }
}
function searchAndDelete(interest_tree, user_tree){
    var interest = Object.keys(interest_tree)[0]
    debugger
    if (Object.keys(interest_tree[interest]).length != 0){
        user_tree[interest] = searchAndDelete(interest_tree[interest], user_tree[interest])
        return user_tree
    }
    else{
        var s = flatten(user_tree[interest])
        for (i in s){
            delete chosen_tags_plain[i]
        }
        delete user_tree[interest]
        delete chosen_tags_plain[interest]
        return user_tree
    }
}
function changeStatus(key){
    var details = document.getElementById(`details ${key}`)
    if (details){
        if (details.open){
            details.open = false
        }
        else{
            details.open = true
        }
    }
    elem = document.getElementById(`${key}`)
    const tree = getFullInheritanceTree(key)
    var mark = document.getElementById(`interests_chosen_mark ${key}`)
    if (key in chosen_tags_plain) {
        article_upload_tags = searchAndDelete(tree, article_upload_tags)
        elem.setAttribute('class', 'interests unselected')
        mark.innerHTML = '&#x2717;'
    }
    else{
        article_upload_tags = searchAndInsert(tree, article_upload_tags)
        interests_plain = Object.assign({}, chosen_tags_plain, flatten(article_upload_tags))
        elem.setAttribute('class', 'interests selected')
        mark.innerHTML = '&#x2713;'
    }
}
function getIndex(interest){
    var mark = `<p onclick="changeStatus('${interest}')" id="interests_chosen_mark ${interest}" style="display: inline-block; font-size: 16;">`
    var index = 'class="interests unselected"'
    mark += '&#x2717;</p>'
    return [index, mark]
}

function displayInterests(interests, summary_name='Your interests', with_indexing=false, add_to_chosen=true, summary_index=['', ''], child_of=''){
    html = `<details id="details ${summary_name}"><summary id="${summary_name}" ${summary_index[0]} child_of="${child_of}">${summary_name}${summary_index[1]}</summary><ul>`
    for (const key in interests){
        
        if (Object.keys(interests[key]).length == 0){
            var index_and_mark = getIndex(key)
            html += `<li id="${key}" ${index_and_mark[0]} child_of="${summary_name}">${key}${index_and_mark[1]}</li>`
        }
        else if(typeof interests[key] == 'object'){
            summary_index = getIndex(key)
            html += displayInterests(interests[key], key, with_indexing, add_to_chosen, summary_index, summary_name)
        }
    }
    html += `</ul></details>`
    return html
}


function loadAllInterests(){
    sendRequest('POST', '/load_info/', {'page': 'personal_data', 'all_interests': true}).then(resp => {
        html = displayInterests(JSON.parse(resp)['interests'], 'All interests', true, false)
        insertHTML('#all_interests', html)
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
