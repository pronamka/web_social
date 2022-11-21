// function now() and throttle() (that used here for 
// sending request properly (to avoid sending to many at)
// once) are taken from https://github.com/jashkenas/underscore.git

function now() {
    return new Date().getTime();
};

function throttle(func, wait, options) {
    var timeout, context, args, result;
    var previous = 0;
    if (!options) options = {};
  
    var later = function() {
      previous = options.leading === false ? 0 : now();
      timeout = null;
      result = func.apply(context, args);
      if (!timeout) context = args = null;
    };
  
    var throttled = function() {
      var _now = now();
      if (!previous && options.leading === false) previous = _now;
      var remaining = wait - (_now - previous);
      context = this;
      args = arguments;
      if (remaining <= 0 || remaining > wait) {
        if (timeout) {
          clearTimeout(timeout);
          timeout = null;
        }
        previous = _now;
        result = func.apply(context, args);
        if (!timeout) context = args = null;
      } else if (!timeout && options.trailing !== false) {
        timeout = setTimeout(later, remaining);
      }
      return result;
    };
  
    throttled.cancel = function() {
      clearTimeout(timeout);
      previous = 0;
      timeout = context = args = null;
    };
  
    return throttled;
  }


const request_url = '/admin_get_posts/'
var posts = {}
var extension_amount = 0

document.addEventListener('DOMContentLoaded', getPosts(2), {once: true});


function sendRequest(method, url, body) {
    const headers = {'Content-Type': 'application/json'}
    return fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: headers}).then(response => {
        return response.text()
    })
}

function getPosts(amount, with_reduced_offset=false){
    if (with_reduced_offset == true){
        extension_amount -= 1
    }
    sendRequest('POST', request_url, 
    {'posts_loaded': extension_amount, 'posts_required': amount}).then(resp => {
        post_json = JSON.parse(resp)
        extension_amount += amount
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
        getPosts(1, true)
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
function load(){
    document.removeEventListener("scroll", load);
    setTimeout(load_on_scroll, '1000');
    document.addEventListener("scroll", load);
}
var load_on_scroll = function(event) {
    
    if ((window.innerHeight+window.scrollY) >= document.body.offsetHeight-100){
        console.log('called')
        getPosts(2);
    } }
document.addEventListener("scroll", throttle(load_on_scroll, 100));
