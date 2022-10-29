const request_url = '/admin_get_posts'
var posts = {}
var extension_amount = -1

document.addEventListener('DOMContentLoaded', getPosts());


function sendRequest(method, url) {
    const headers = {'Content-Type': 'application/json'}
    extension_amount = extension_amount+1;
    return fetch(url, {
        method: method,
        body: JSON.stringify(extension_amount),
        headers: headers}).then(response => {
        return response.text()
    })
}

function getPosts(){
    sendRequest('POST', request_url).then(resp => {
        post_json = JSON.parse(resp);
        buildPosts(post_json);
    })
}
function buildPosts(post_dict){
    for (var i=0, l=Object.keys(post_dict).length; i<=l; i++){
        var comments = '';
        try{
            comments = buildComments(post_dict[i]['comment_registry']['comments']);
            title = post_dict[i]['title'];
            author = post_dict[i]['author'];
            post_id = post_dict[i]['post_id'];
            path = '/static/upload_folder/'+title;
            if (comments==''){
                comments='<ul><li>No comments yet</li></ul>'
            }
            post = buildHTML(path, author, title, post_id, comments);
            addPost(post);
        }
        catch(error){
            if (error != "TypeError: Cannot read properties of undefined (reading 'comment_registry')"){
                console.log(`An error has occured:` +error+`\nPlease, contact our leading backend developer at defender0508@gmail.com`);
            }
            else {
                comments = 'No comments yet.'
            }
        }
    }
}
function buildHTML(path, author, title, post_id, comments){
    html = `<div class="table_cell">
            <iframe width="400" height="500" src="`+ path+`"></iframe>
            <details class="post_data" open>
                <summary>Post information</summary>
                <ul>
                <li>Title: `+title+`</li>
                <li>Author: `+author+`</li>
                <li>Post id: `+post_id+`</li>
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
    const tab = document.getElementById('posts_table');
    var template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    tab.appendChild(template.content);
    return template.content.firstChild;
}

`function load_on_scroll(){}
    $(document).ready(function(){
        $(window).bind('scroll', extensionNeedChecker)
        function extensionNeedChecker(){
            console.log($(document).height())
            console.log($(window).height())
            if ($(window).scrollTop() >= $(document).height()-$(window).height() - 300){
                getPosts();
            }
        }
    })`
current_position = 250
window.addEventListener("scroll", function(event) {
    var top = this.scrollY
    console.log(top, current_position)
    if (current_position < top){
        current_position += 1000
        getPosts();
    } 
}, false);