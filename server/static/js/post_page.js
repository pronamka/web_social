const comment = document.getElementById('comment')
const load_comments_btn = document.getElementById('load_comments_btn')


const settings = {'page': 'comments', 
                    'object_id': post_id, 
                    'comments_loaded': 0, 
                    'comments_required': 5, 
                    'of_user': 0}
const comments_with_replies = {}
document.addEventListener('DOMContentLoaded', loadComments())

function sendRequest(method, url, body) {
    const headers = {'Content-Type': 'application/json'}
    return fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: headers}).then(response => {
        return response.text()
    })
}
class LikeButton{
    constructor(button_item){
        this.button = button_item
        this.states = {}
        this.states['1'] = {'action': 0, 'status': '0'}
        this.states['0'] = {'action': 1, 'status': '1'}
        this.styles = {}
        this.styles['0'] = {'b_c': 'red', 't_c': 'white', 't': 'Like'}
        this.styles['1'] = {'b_c': 'grey', 't_c': 'white', 't': 'Liked'}
        this.status = this.defineStatus()
        
    }
    defineStatus(){
        
        console.log(current_status)
        this.setStyleSheet(current_status)
        return current_status
    }
    changeStatus(){
        const new_status = this.states[this.status]['status']
        fetch(`/like_post/?post_id=${post_id}&new_status=${this.states[this.status]['action']}`, {method: 'GET'} ).then(resp => {
            this.setStyleSheet(new_status)
            this.status = new_status
        })
    }
    setStyleSheet(style_sheet_name){
        
        this.button.style.backgroundColor = this.styles[style_sheet_name]['b_c']
        this.button.style.color = this.styles[style_sheet_name]['t_c']
        this.button.firstChild.data =this.styles[style_sheet_name]['t']
    }
}
class subscribeButton{
    constructor(button_item){
        this.button = button_item
        this.status = this.defineStatus()
        this.states = {'subscribed': {'action': 0, 'status': 'unsubscribed'}, 
                    'unsubscribed': {'action': 1, 'status': 'subscribed'}}
    }
    defineStatus(){
        const protocols = {'1': 'subscribed', '0': 'unsubscribed'}
        
        this.setStyleSheet(protocols[current_status])
        return protocols[current_status]
    }
    changeStatus(){
        const new_status = this.states[this.status]['status']
        sendRequest('POST', '/change_subscriptions/', 
        {'author_id': author_id, 'action': this.states[this.status]['action']}).then(resp => {
            this.setStyleSheet(new_status)
            this.status = new_status
        })
    }
    setStyleSheet(style_sheet_name){
        const styles = {'unsubscribed': {'b_c': 'red', 't_c': 'white', 't': 'Subscribe'},
                    'subscribed': {'b_c': 'grey', 't_c': 'white', 't': 'Subscribed'}}
        this.button.style.backgroundColor = styles[style_sheet_name]['b_c']
        this.button.style.color = styles[style_sheet_name]['t_c']
        this.button.firstChild.data =styles[style_sheet_name]['t']
    }
}
const subscribe_btn = new subscribeButton(document.getElementById('subscribe-btn'))
const like_btn = new LikeButton(document.getElementById('like-btn'))
function change_subscriptions(){
    subscribe_btn.changeStatus()
}

function sendComment(post_id){
    if (!comment.value){
        alert('You did not put in any text.')
        return 0;
    }
    sendRequest('POST', '/comment/', {'post_id': post_id, 
    'comment_text': comment.value}).then(resp=>{
        const comment_dict = JSON.parse(resp)
        addComment(comment_dict, true)
    })
}

function loadComments(){
    sendRequest('POST', '/load_info/', settings).then(resp=>{
        comments_dict = JSON.parse(resp)
        settings['comments_loaded'] += settings['comments_required']
        buildComments(comments_dict['latest_comments'])
    })}

function buildComments(comments, direction='#comments_dv'){ 
    var comment_amount = 0
    if(comments != null){
        const comment_amount = Object.keys(comments).length-1
        for (var i=0, l=comment_amount; i<=l; i++){
            var new_comment = new Comment(comments[i])
            addComment(new_comment, false, direction)
        }
    }
    if (comment_amount < 4){
        load_comments_btn.remove()
    }
}
function addComment(comment, insert_before=false, direction = '#comments_dv'){
    html = `<div class="comment" id="comment ${comment.id}">
        <em><strong>${comment.author}</strong>, \t ${comment.date}</em>
        <p class="comment_text">${comment.text}</p>
        <div id="comment-replies ${comment.id}" class="replies-wrapper"></div>`
    if (comment.replies_amount != 0){
        html+= `<button id='see_replies_btn ${comment.id}' 
        onclick="loadReplies(${comment.id})">${comment.replies_amount} replies</button>`
        comments_with_replies[comment.id] = [0, 5]
    }
    html += `<button onclick="reply(${comment.id})" id="comment_reply ${comment.id}">Reply</button></div>`
    insertHTML(direction, html, insert_before)
}
function loadReplies(comment_id){
    const cur_comment = comments_with_replies[comment_id]
    sendRequest('POST', '/load_info/', {'object_id': comment_id, 'object_type':'reply',
    'comments_loaded': cur_comment[0], 'comments_required': cur_comment[1], page: 'comments'}).then(resp=>{
        console.log(resp)
        comments_with_replies[comment_id][0] += cur
        buildComments(JSON.parse(resp)['latest_comments'], false, `#comment-replies ${comment_id}`)
    }
    )
}
function reply(comment_id){
    node = document.getElementById(`comment_reply ${comment_id}`)
    html = `<textarea id="comment_reply_text ${comment_id}" placeholder="Reply..."></textarea>
    <button onclick="sendReply(${comment_id})" id="send_reply_btn ${comment_id}">Send</button>`
    template = document.createElement('template')
    template.innerHTML = html
    document.getElementById(`comment ${comment_id}`).insertBefore(template.content, node.nextSibling)
    document.getElementById(`comment_reply ${comment_id}`).remove()
}
function sendReply(comment_id){
    console.log(comment_id)
    var reply_text = document.getElementById(`comment_reply_text ${comment_id}`).value
    if (reply_text.length == 0){
        alert("You haven't written anything yet")
    }
    else{
        sendRequest('POST', '/comment/', {'post_id': null,
        'comment_text': reply_text, 'is_reply': comment_id}).then(resp=>{
            document.getElementById(`comment_reply_text ${comment_id}`).remove()
            document.getElementById(`send_reply_btn ${comment_id}`).remove()
            var load_replies_button = document.getElementById(`see_replies_btn ${comment_id}`)
            if (load_replies_button == null){
                node=document.getElementById(`comment_reply ${comment_id}`)
                html = `<button id='see_replies_btn ${comment_id} 
                onclick="loadReplies(${comment_id})">1 reply</button>`
                template = document.createElement('template')
                template.innerHTML = html
                document.getElementById(`comment ${comment_id}`).insertBefore(template.content, node)
            }
        })
    }
}
class Comment{
    constructor(comment){
        this.comment_id = comment['comment_id'];
        this.comment_author = comment['author'];
        this.creation_date = comment['made_ago'];
        if (comment['made_ago'] == 0){
            this.creation_date = 'Today'
        }
        else{
            this.creation_date = comment['made_ago'] + ' ago';
        }
        this.comment = comment['text'];
        this.replies_num = comment['replies_amount']
    }
    get allValues(){
        return (this.author, this.creation_date, this.text);
    }
    get author(){
        return this.comment_author
    }
    get date(){
        return this.creation_date
    }
    get text(){
        return this.comment
    }
    get replies_amount(){
        return this.replies_num
    }
    get id(){
        return this.comment_id
    }
    
}
function insertHTML(direction, html, insert_before=false) {
    const tab = document.querySelector(direction);
    var template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    if (insert_before==false){
        tab.appendChild(template.content);
        return template.content.firstChild;
    }
    else{
        console.log(tab, tab.firstChild, template)
        tab.insertBefore(template.content, tab.firstChild)
        return template.content.firstChild;
    }
}