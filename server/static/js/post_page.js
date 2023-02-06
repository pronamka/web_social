
class LikeButton{
    constructor(button_item){
        this.button = button_item
        this.states = {}
        this.states['1'] = {'action': 0, 'status': '0'}
        this.states['0'] = {'action': 1, 'status': '1'}
        this.styles = {}
        this.styles['0'] = {'text': '<i class="fa-regular fa-thumbs-up"></i> ', 'f': this.decreaseLikes}
        this.styles['1'] = {'text': '<i class="fa-solid fa-thumbs-up"></i> ', 'f': this.increaseLikes}
        this.status = this.defineStatus()
        
    }
    decreaseLikes(){
        likes_amount -= 1;
        console.log(likes_amount)
    }
    increaseLikes(){
        likes_amount += 1;
        console.log(likes_amount)
    }
    defineStatus(){
        this.setStyleSheet(is_liked);
        return is_liked;
    }
    changeStatus(){
        const new_status = this.states[this.status]['status']
        this.styles[new_status]['f']()
        fetch(`/like_post/?post_id=${post_id}&new_status=${this.states[this.status]['action']}`, {method: 'GET'} ).then(resp => {
            this.setStyleSheet(new_status)
            this.status = new_status
            
        })
    }
    setStyleSheet(style_sheet_name){
        this.button.innerHTML = this.styles[style_sheet_name]['text'] + likes_amount
    }
}

class subscribeButton{
    constructor(button_item){
        this.button = button_item
        this.states = {'subscribed': {'action': 0, 'status': 'unsubscribed'}, 
                    'unsubscribed': {'action': 1, 'status': 'subscribed'}}
        this.styles = {'unsubscribed': {'background-color': '#403232', 'text-color': 'white', 'text': 'Subscribe', 'f': this.decreaseSubscriptions},
        'subscribed': {'background-color': 'rgba(198, 188, 188, 0.37)', 'text-color': 'black', 'text': 'Subscribed', 'f': this.increaseSubscriptions}}
        this.status = this.defineStatus()
        this.subscribers_amount_label = document.getElementById('subscribers-amount')
    }

    decreaseSubscriptions(){
        subscribers_amount -= 1;
    }

    increaseSubscriptions(){
        subscribers_amount += 1;
    }

    defineStatus(){
        const protocols = {'1': 'subscribed', '0': 'unsubscribed'}
        this.setStyleSheet(protocols[is_subscribed])
        return protocols[is_subscribed]
    }
    changeStatus(){
        const new_status = this.states[this.status]['status']
        this.styles[new_status]['f']()
        sendRequest('POST', '/change_subscriptions/', 
        {'author_id': author_id, 'action': this.states[this.status]['action']}).then(resp => {
            this.setStyleSheet(new_status)
            this.status = new_status
            console.log(this.subscribers_amount)
            this.subscribers_amount_label.innerHTML = subscribers_amount + ' subscribers'
        })
    }
    setStyleSheet(style_sheet_name){
        this.button.style.backgroundColor = this.styles[style_sheet_name]['background-color']
        this.button.style.color = this.styles[style_sheet_name]['text-color']
        this.button.firstChild.data = this.styles[style_sheet_name]['text']
    }
}



class Comment{
    constructor(comment){
        this.comment_id = comment['comment_id'];
        this.comment_author = comment['author'];
        this.creation_date = comment['made_ago'];
        this.author_avatar = comment['author_avatar'];
        if (comment['made_ago'] == 0){
            this.creation_date = 'Today'
        }
        else{
            this.creation_date = comment['made_ago'] + ' days ago';
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



class CommentHTMLBuilder{
    constructor(comment, insert_before_all_children=false, insert_into_element_id='#comments_dv'){
        this.comment = comment
        this.insert_before_all_children = insert_before_all_children
        this.insert_into_element_id = insert_into_element_id
        this.html = ''
        this.buildMainComment()
        this.buildReplyButton()
        this.buildTextAreaForReply()
        this.buildLoadRepliesButton()
        this.buildRepliesSection()
        
        this.comment_html += '</div>'
    }

    buildMainComment(){
        this.html += 
        `<div class="comment" id="comment-${this.comment.id}">
            <div class="comment-main-content">
                <img src="/${this.comment.author_avatar}" class='comment-author-avatar'>
                <em class="comment-author-and-date-container">
                    <strong class="comment-author-name">
                        ${this.comment.author}
                    </strong>, 
                    \t ${this.comment.date}
                </em>
                <p class="comment-text">${this.comment.text}</p>
            </div>`
    }

    buildRepliesSection(){
        this.html += 
        `<div class="replies-section" id="replies-section ${this.comment.id}" style="display: none">
            <div id="comment-replies-${this.comment.id}" class="replies-wrapper"></div>
            <button class="load-more-replies-button" onclick="loadReplies(${this.comment.id})"
            id="load-more-replies-button ${this.comment.id}">
                &#8627; Load More
            </button>
        </div>`
    }

    buildLoadRepliesButton(){
        var display = 'none'
        if (this.comment.replies_amount != 0){
            display = 'inline-block'
        }
        this.html += 
            `<div class='load-replies-wrapper' 
            id="load-replies-wrapper ${this.comment.id}" style="display: ${display}">
                <button id='load-replies-button ${this.comment.id}' class='load-replies-button' 
                onclick="defineButtonAction(${this.comment.id})" 
                value="${this.comment.replies_amount}">
                    &#9660; ${this.comment.replies_amount} replies
                </button>
            </div>`
        comments_with_replies[this.comment.id] = [0, 5]
    }

    buildReplyButton(){
        this.html += `<button onclick="showTextAreaForReply(${this.comment.id})" 
        id="reply-to-comment-button-${this.comment.id}" class="reply-to-comment-button">
            Reply
        </button>`
    }

    buildTextAreaForReply(){
        this.html += 
            `<div class="reply-to-comment-wrapper" style="display: none" 
            id="reply-to-comment-wrapper ${this.comment.id}">
                <textarea id="comment-reply-input ${this.comment.id}" class="comment-reply-input" placeholder="Reply..."></textarea>
                <div class='reply-buttons-wrapper'>
                    <button class='cancel-sending-reply-button' onclick='hideTextAreaForReply(${this.comment.id})'>
                            Cancel
                    </button>
                    <button onclick="postReply(${this.comment.id})" class="send-reply-button" 
                    id="send-reply-button ${this.comment.id}">
                        Send
                    </button>
                </div>
            </div>`
    }

    insertCommentIntoDocument(){
        insertHTML(this.insert_into_element_id, this.html, this.insert_before_all_children)
        document.getElementById(`comment-reply-input ${this.comment.id}`).addEventListener('input', resizeTextArea)
    }
}

function defineButtonAction(comment_id){
    const replies = document.getElementById(`replies-section ${comment_id}`)
    const load_replies_btn = document.getElementById(`load-replies-button ${comment_id}`)
    if (replies.style.display != 'none'){
        replies.style.display = 'none'
        load_replies_btn.innerHTML= `&#9660; ${load_replies_btn.value} replies`
    }
    else{
        loadReplies(comment_id)
        replies.style.display = 'block'
        load_replies_btn.innerHTML = `&#9650; ${load_replies_btn.value} replies`
        
    }
}


function showTextAreaForReply(comment_id){
    document.getElementById(`reply-to-comment-button-${comment_id}`).style.display='none'
    document.getElementById(`reply-to-comment-wrapper ${comment_id}`).style.display='block'
}

function hideTextAreaForReply(comment_id){
    document.getElementById(`reply-to-comment-button-${comment_id}`).style.display='block'
    var reply_to_comment_wrapper = document.getElementById(`reply-to-comment-wrapper ${comment_id}`)
    reply_to_comment_wrapper.style.display = 'none'
    reply_to_comment_wrapper.value = ''
}



function change_subscriptions(){
    subscribe_btn.changeStatus()
}


function sendComment(post_id){
    // checking if the user filled the comment field 
    // not to send the request with empty comment text
    if (!comment.value){
        alert('You did not put in any text.')
        return 0;
    }
    // send request if there is text
    sendRequest('POST', '/comment/', {'post_id': post_id, 'comment_text': comment.value})
    .then(resp=>{
        // the server response will contin all information, 
        // that could not be defined on the client side (the id of the comment)
        const comment_dict = JSON.parse(resp)

        // then the comment is inserted into the document
        new CommentHTMLBuilder( new Comment(comment_dict), true, "#comments_dv").insertCommentIntoDocument()
        document.getElementById('comment-input').value = ''
    })
}


function loadComments(){
    sendRequest('POST', '/load_info/', settings).then(resp=>{
        comments_dict = JSON.parse(resp)
        settings['comments_loaded'] += settings['comments_required']
        buildComments(comments_dict['latest_comments'])
        if (comments_dict['latest_comments'].length < 5){
            document.getElementById('load-comments-button').style.display = 'none'
        }
    })
}




function buildComments(comments, direction='#comments_dv'){ 
    var comment_amount = 0
    if(comments != null){
        const comment_amount = Object.keys(comments).length-1
        for (var i=0, l=comment_amount; i<=l; i++){
            var comment = new Comment(comments[i])
            new CommentHTMLBuilder(comment, false, direction).insertCommentIntoDocument()
        }
    }
}


function manageLoadRepliesButton(comment_id, loaded_replies_amount){
    const load_replies_button = document.getElementById(`load-more-replies-button ${comment_id}`)
    if(loaded_replies_amount< 5){
        load_replies_button.style.display='none'
    }
    else{
        return 0;
    }
}


function loadReplies(comment_id){
    document.getElementById(`comment-replies-${comment_id}`).style.display = 'block'
    const cur_comment = comments_with_replies[comment_id]
    sendRequest('POST', '/load_info/', {'object_id': comment_id, 'object_type':'reply',
    'comments_loaded': cur_comment[0], 'comments_required': cur_comment[1], page: 'comments'}).then(resp=>{
        resp = JSON.parse(resp)
        comments_with_replies[comment_id][0] += resp['latest_comments'].length
        buildComments(resp['latest_comments'], `#comment-replies-${comment_id}`)
        manageLoadRepliesButton(comment_id, resp['latest_comments'].length,)
    }
    )
}

function sendReply(comment_id, reply_text){
    sendRequest('POST', '/comment/', {'post_id': post_id,
        'comment_text': reply_text, 'is_reply': comment_id}).then(resp=>{
            const load_replies_button = document.getElementById(`load-replies-button ${comment_id}`)
            const replies_amount = Number(load_replies_button.value) + 1
            load_replies_button.value = replies_amount
            load_replies_button.textContent = `${replies_amount} replies`
        })
}


function postReply(comment_id){
    var reply_text = document.getElementById(`comment-reply-input ${comment_id}`).value
    if (reply_text.length == 0){
        alert("You haven't written anything yet")
    }
    else{
        sendReply(comment_id, reply_text)
        document.getElementById(`reply-to-comment-wrapper ${comment_id}`).style.display='none'
        document.getElementById(`load-replies-wrapper ${comment_id}`).style.display = 'inline-block'
        hideTextAreaForReply(comment_id)
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



const comment = document.getElementById('comment-input')
const load_comments_btn = document.getElementById('load_comments_btn')
var load_on_scroll_disabled = true


const settings = {'page': 'comments', 
                    'object_id': post_id, 
                    'comments_loaded': 0, 
                    'comments_required': 5, 
                    'of_user': 0}
const comments_with_replies = {}

const subscribe_btn = new subscribeButton(document.getElementById('subscribe-btn'))
const like_btn = new LikeButton(document.getElementById('like-btn'))

document.addEventListener('DOMContentLoaded', loadComments())

document.getElementById('comment-input').addEventListener('input', resizeTextArea)

