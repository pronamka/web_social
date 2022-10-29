const request_url = '/extend_sub_posts';

var extension_counter = -1;

document.addEventListener('DOMContentLoaded', getPosts());

/**
function sendRequest(url, method){
    const request_headers = {'Content-Type': 'application/json'}
    console.log(method)
    extension_counter = extension_counter + 1;
    return fetch(url, {
        mehtod: 'POST',
        body: JSON.stringify(extension_counter),
        headers: request_headers
    }).then(response => {
        return response.text();
    })
} */
function sendRequest(method, url) {
    const headers = {'Content-Type': 'application/json'}
    extension_counter = extension_counter+1;
    return fetch(url, {
        method: method,
        body: JSON.stringify(extension_counter),
        headers: headers}).then(response => {
        return response.text()
    })
}

function getPosts(){
    sendRequest('POST', request_url).then(resp => {
        posts_dict = JSON.parse(resp);
        buildPosts(posts_dict);
    })
}
function buildPosts(post_dict){
    date = post_dict['date']
    delete post_dict['date']
    addHTML('<h3>'+date+'</h3>')
    for (var i=0, l=Object.keys(post_dict).length; i<=l; i++){
        try{
            title = post_dict[i]['title'];
            author = post_dict[i]['author'];
            post_id = post_dict[i]['post_id'];
            path = '/static/upload_folder/'+title;
            post = buildHTML(path, author, title, post_id);
            addHTML(post);
        }
        catch(error){
            console.log(error);
        }
    }
    addHTML('<div class="ln-dates-sep"></div>')
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

$(document).ready(function(){
    $(window).bind('scroll', extensionNeedChecker)
    function extensionNeedChecker(){
        if ($(window).scrollTop() >= $(document).height()-$(window).height() - 300){
            $(window).unbind('scroll', extensionNeedChecker);
            getPosts();
        }
    }
})
