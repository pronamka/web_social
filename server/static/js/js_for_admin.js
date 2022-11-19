const request_url = '/admin_get_posts/'
var posts = {}
var extension_amount = 0

document.addEventListener('DOMContentLoaded', getPosts(2));


function sendRequest(method, url, body) {
    const headers = {'Content-Type': 'application/json'}
    return fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: headers}).then(response => {
        return response.text()
    })
}

function getPosts(amount){
    sendRequest('POST', request_url, 
    {'posts_loaded': extension_amount, 'posts_required': amount}).then(resp => {
        post_json = JSON.parse(resp)
        console.log(extension_amount)
        extension_amount += amount
        console.log(extension_amount)
        buildPosts(post_json);
    })
}
function buildPosts(post_dict){
    console.log(post_dict)
    for (var i=0, l=Object.keys(post_dict).length-1; i<=l; i++){
        try{
            title = post_dict[i]['title'];
            author = post_dict[i]['author'];
            post_id = post_dict[i]['post_id'];
            creation_date = post_dict[i]['display_date']
            path = '/static/upload_folder/'+title;
            post = buildHTML(path, author, title, post_id, creation_date);
            addPost(post);
        }
        catch(error){
            if (error != "TypeError: Cannot read properties of undefined (reading 'comment_registry')"){
                console.log('An error has occured:'+error)
            }
            else {
                comments = 'No comments yet.'
            }
        }
    }
}
function buildHTML(path, author, title, post_id, creation_date){
    html = `<div class="table_cell" id="${post_id}">
            <iframe width="400" height="500" src="${path}"></iframe>
            <button onclick="verify_post(${post_id});">Verify</button>
            <button onclick="window.location.href='/admin/examine_post/?post_id=${post_id}'" 
            id="examine_post_btn ${post_id}">Examine</button>
            <details class="post_data" open>
                <summary>Post information</summary>
                <ul>
                <li>Title: ${title}</li>
                <li>Author: ${author}</li>
                <li>Post id: ${post_id}</li>
                <li>Created on:${creation_date}</li>
                </ul>
            </details>
        </div>`;
    return html
}
function verify_post(post_id){
    sendRequest('POST', '/admin/verify_post/', {'post_id': post_id}).then(resp => {
        const verified_post = document.getElementById(post_id)
        verified_post.remove()
        getPosts(1)
    }
    )
}


function addPost(html) {
    const tab = document.getElementById('posts_table');
    var template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    tab.appendChild(template.content);
    return template.content.firstChild;
}
window.addEventListener("scroll", function(event) {
    if ((window.innerHeight+window.scrollY) >= document.body.offsetHeight-100){
        getPosts(2);
    } 
}, false);
