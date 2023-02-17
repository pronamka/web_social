class Comment{
    constructor(comment_info){
        this.comment_id = comment_info['comment_id']
        this.author_val = comment_info['author']
        this.date_val = comment_info['date']
        this.text_val = comment_info['text']
        this.post_id_val = comment_info['post_id']
        this.replies_amount_val = comment_info['replies_amount']
        this.post_title_val = comment_info['post_title']
        this.status = comment_info['status']
    }
    get id(){
        return this.comment_id
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
    get replies_amount(){
        return this.replies_amount_val
    }
    get post_title(){
        return this.post_title_val
    }

}

class CommentsBuilder{
    constructor(status, comments, loaded_comments){
        this.comments = comments
        this.status = status
        this.comments_amount = comments.length
        this.loaded_comments = loaded_comments
    }

    buildComments(){
        if(this.comments_amount == 0){
            return 0;
        }

        for(var i = 0; i < this.comments_amount; i++){
            this.buildComment(this.comments[i])
        }
        return this.loaded_comments
    }

    buildCommentHTML(comment){
        const comment_html = `
        <div class="comments-table-row" id="comment-row-${comment.id}">
            <button id="show-comment-replies-button-${comment.id}" title="Click to see replies" class="load-replies-button">${comment.replies_amount} &#9660;</button>
            <p class="comment-info">${comment.author}</p>
            <p class="comment-info">${comment.text}</p>
            <p class="comment-info">${comment.date}</p>
            <p class="comment-info">${comment.post_title}</p>

            <button id="comment-approve-button-${comment.id}" class="approve-comment-button">
                <i class="fa-solid fa-check"></i>
            </button>
            <button id="comment-ban-button-${comment.id}" class="ban-comment-button">
                <i class="fa-solid fa-ban"></i>
                </button>
            <button id="comment-reply-button-${comment.id}" class="reply-to-comment-button">
                <i class="fa-solid fa-reply"></i>
            </button>

            <div id="comment-replies-container-${comment.id}" class="replies-row" style="display: none">
                <div id="comment-replies-row-${comment.id}" 
                    class="comments-table-row"></div>
                <button id="load-comment-replies-button-${comment.id}" class="load-comment-replies-button load-button">&#8627; More Replies</button>
            </div>
            
        </div>`
        return comment_html
    }

    buildComment(comment_){

        const comment = new Comment(comment_)
        if (this.loaded_comments[comment.id] != undefined){
            return 
        }
        try{
            this.loaded_comments[`${comment.id}`] = 1
        }
        catch{
            console.log(`Error on ${comment.id}`)
        }
        insertHTML(this.status, this.buildCommentHTML(comment))

        this.addActionsToButtons(comment)
    }

    addActionsToButtons(comment){
        if(comment.replies_amount > 0){
            $(`#show-comment-replies-button-${comment.id}`).on('click', ()=>{
                comments_table_builder.openReplies(comment.id)
            })

            $(`#load-comment-replies-button-${comment.id}`).on('click', ()=>{
                comments_table_builder.loadReplies(comment.id)
            })
        }

        else{
            document.querySelector(`#show-comment-replies-button-${comment.id}`).disabled = true
            document.querySelector(`#load-comment-replies-button-${comment.id}`).disabled = true
        }
        if(comment.status != 3){
            if(comment.status == 0){
                $(`#comment-approve-button-${comment.id}`).on('click', ()=>{
                    markAsSeen(comment.id, comment.author, comment.text, comment.post_id)
                })
            }
            else{
                document.querySelector(`#comment-approve-button-${comment.id}`).disabled = true
                document.querySelector(`#comment-approve-button-${comment.id}`).innerHTML = '<i class="fa-solid fa-check-double"></i>'
            }
            $(`#comment-reply-button-${comment.id}`).on('click', ()=>{
                reply(comment.id, comment.author, comment.text, comment.date, comment.post_id)
            })
    
            $(`#comment-ban-button-${comment.id}`).on('click', ()=>{
                ban(comment.id, comment.author, comment.text, comment.date, comment.post_id)
            })
        }

        else{
            document.querySelector(`#comment-approve-button-${comment.id}`).disabled = true
            document.querySelector(`#comment-ban-button-${comment.id}`).disabled = true
            document.querySelector(`#comment-reply-button-${comment.id}`).disabled = true
        }
        
    }
}


class CommentsTableBuilder{
    constructor(){
        this.current_tab = 'unseen_comments'

        this.comments_with_replies = {}
        this.comments_page_tabs = 
        {
            'unseen': 
                {'comments_loaded': 0, 
                'comments_required': 10},
            'seen':
                {'comments_loaded': 0, 
                'comments_required': 10},
            'replied':
                {'comments_loaded': 0, 
                'comments_required': 10},
            'banned': 
                {'comments_loaded': 0, 
                'comments_required': 10},
        }

        this.status_codes = {'unseen': 0, 'seen': 1, 'replied': 2, 'banned': 3}

        this.status_table_tabs = 
        {
            'unseen': '#unseen-comments-table', 
            'seen': '#seen-comments-table', 
            'replied': '#received-author-reply-comments-table', 
            'banned': '#banned-comments-table'
        }

        this.load_more_comments_buttons = 
        {
            'unseen': '#load-more-unseen-comments-button', 
            'seen': '#load-more-seen-comments-button', 
            'replied': '#load-more-received-author-reply-comments-button', 
            'banned': '#load-more-banned-comments-button'
        }

        this.comments_replies = {}

        this.loaded_comments = {}
    }

    formCommentsRequest(status){
        var request_parameters = {
            'page': 'comment_section', 
            'comments_loaded': this.comments_page_tabs[status]['comments_loaded'], 
            'comments_required': this.comments_page_tabs[status]['comments_required'], 
            'comment_status': this.status_codes[status]
        
        }
        return request_parameters
    }
    
    loadComments(status){
        var request_parameters = this.formCommentsRequest(status)

        sendRequest('POST', '/load_info/',request_parameters).then(resp=>{
            this.comments_page_tabs[status]['comments_loaded'] += 
                this.comments_page_tabs[status]['comments_required']
            this.displayComments(status, JSON.parse(resp)['comments_for_authors'])
        })
    }

    displayComments(status, comments){
        if(comments.length < this.comments_page_tabs[status]['comments_required']){
            document.querySelector(this.load_more_comments_buttons[status]).disabled = true
        }
        const comments_html = new CommentsBuilder(this.status_table_tabs[status], comments, this.loaded_comments)
        this.loaded_comments = comments_html.buildComments()
    }

    openReplies(comment_id){

        const replies_container = document.getElementById(`comment-replies-container-${comment_id}`)
        const show_replies_button = document.getElementById(`show-comment-replies-button-${comment_id}`)
        if(replies_container.style.display == 'none'){
            var comment = this.comments_replies[comment_id]
            show_replies_button.innerHTML = show_replies_button.innerHTML.slice(0, -1) + '&#9650;'
            if(comment == undefined){
                this.comments_replies[comment_id] = {'comments_loaded': 0, 'comments_required': 5}
                this.loadReplies(comment_id)
            }
            replies_container.style.display = 'grid';
        }
        else{
            show_replies_button.innerHTML = show_replies_button.innerHTML.slice(0, -1) + '&#9660;'
            replies_container.style.display = 'none'
        }
    }

    formRepliesRequest(comment_id){
        const request_parameters = {
            'page': 'comments', 
            'object_id': comment_id, 
            'comments_required': this.comments_replies[comment_id]['comments_required'], 
            'comments_loaded': this.comments_replies[comment_id]['comments_loaded'], 
            'object_type': 'reply',
            'show_banned': true}
        
        return request_parameters
    }

    
    loadReplies(comment_id){
        const request_parameters = this.formRepliesRequest(comment_id)

        sendRequest('POST', '/load_info/', request_parameters).then(resp=>{
            const replies = JSON.parse(resp)['latest_comments']
            console.log(replies)
            this.comments_replies[comment_id]['comments_loaded'] += replies.length
            this.displayReplies(comment_id, replies)
        })
    }

    displayReplies(comment_id, replies){
        if (replies.length < this.comments_replies[comment_id]['comments_required']){
            $(`#load-comment-replies-button-${comment_id}`).off('click')
            document.querySelector(`#load-comment-replies-button-${comment_id}`).disabled = true
        }

        const comments_html = new CommentsBuilder(`#comment-replies-row-${comment_id}`, replies, this.loaded_comments)
        this.loaded_comments = comments_html.buildComments()
    }
}

function reply(id, author, text, date, post_id){
    var reply_dialog = document.querySelector('#reply-dialog')
    $('#reply-dialog-comment-author-name').html(`Author: ${author}`)
    $('#reply-dialog-comment-text').html(`Text: ${text}`)
    $('#reply-dialog-comment-creation-date').html(`Creation Date: ${date}`)
    $('#reply-dialog-send-reply-button').on('click', ()=>{
        sendReplyRequest(id, post_id)
    })
    reply_dialog.showModal()
}


function sendReplyRequest(comment_id, post_id){
    const reply_text = document.getElementById(`reply-dialog-textarea`).value
    if(reply_text == ''){
        alert('You have not written anything.')
        return 0;
    }


    sendRequest('POST', '/comment/', {'post_id': post_id, 
        'comment_text': reply_text, 'is_reply': comment_id}).then(resp=>{
            document.getElementById(`reply-dialog-textarea`).value = ''
            document.querySelector('#reply-dialog').close()
            
            const comment_container = document.querySelector(`#comment-row-${comment_id}`)
            
            if(comment_container.parentElement.id.slice(0, 19) != 'comment-replies-row'){
                const table  = document.querySelector(`#received-author-reply-comments-tables-div`)
                document.querySelector(`#comment-row-${comment_id}`).remove()
                table.insertBefore(comment_container, table.firstChild)
            }
            $(`#comment-approve-button-${comment_id}`).off('click')
            document.querySelector(`#comment-approve-button-${comment_id}`).disabled = true
            document.querySelector(`#comment-approve-button-${comment_id}`).innerHTML = '<i class="fa-solid fa-check-double"></i>'
        })
}


function ban(id, author, text, date, post_id){
    var ban_dialog = document.querySelector('#ban-comment-dialog')
    $('#ban-comment-dialog-comment-author-name').html(`Author: ${author}`)
    $('#ban-comment-dialog-comment-text').html(`Text: ${text}`)
    $('#ban-comment-dialog-comment-creation-date').html(`Creation Date: ${date}`)
    $('#ban-comment-dialog-ban-button').on('click', ()=>{
        sendBanRequest(id)
    })
    ban_dialog.showModal()
}


function sendBanRequest(comment_id){
    const reason = document.getElementById(`ban-comment-dialog-textarea`).value

    sendRequest('POST', '/ban_comment/', {'comment_id': comment_id, 
    'reason': reason}).then(resp=>{
        document.getElementById(`ban-comment-dialog-textarea`).value = ''
        document.querySelector('#ban-comment-dialog').close()

        const comment_container = document.querySelector(`#comment-row-${comment_id}`)

        if(comment_container.parentElement.id.slice(0, 19) != 'comment-replies-row'){
            const table = document.querySelector(`#banned-comments-tables-div`)
            document.querySelector(`#comment-row-${comment_id}`).remove()
            table.insertBefore(comment_container, table.firstChild)
        }

        
        $(`#comment-approve-button-${comment_id}`).off('click')
        $(`#comment-ban-button-${comment_id}`).off('click')
        $(`#comment-reply-button-${comment_id}`).off('click')

        document.querySelector(`#comment-approve-button-${comment_id}`).disabled = true
        document.querySelector(`#comment-approve-button-${comment_id}`).innerHTML = '<i class="fa-solid fa-check"></i>'

        document.querySelector(`#comment-ban-button-${comment_id}`).disabled = true
        document.querySelector(`#comment-reply-button-${comment_id}`).disabled = true

    })
}

function markAsSeen(comment_id){
    sendRequest('POST', '/mark_comment_as_seen/', {'comment_id': comment_id}).then(resp=>{
        const comment_container = document.querySelector(`#comment-row-${comment_id}`)
        if(comment_container.parentElement.id.slice(0, 19) != 'comment-replies-row'){
            document.querySelector(`#comment-row-${comment_id}`).remove()
            document.querySelector(`#seen-comments-tables-div`).insertBefore(comment_container, 
                document.querySelector(`#seen-comments-tables-div`).firstChild)
        }
        
        $(`#comment-approve-button-${comment_id}`).off('click')
        document.querySelector(`#comment-approve-button-${comment_id}`).disabled = true
        document.querySelector(`#comment-approve-button-${comment_id}`).innerHTML = '<i class="fa-solid fa-check-double"></i>'
    })
}

function linkNavTabsToTables(){
    table_nav_tabs.forEach(tab=>{
        tab.addEventListener('click', ()=>{
            const direction = document.querySelector(tab.getAttribute('href'));
            table_nav_tabs.forEach(table_nav_tab => {
                table_nav_tab.classList.remove('table-nav-tab-active')
            })
            tab.classList.add('table-nav-tab-active')

            table_tabs.forEach(table_tab => {
                table_tab.classList.remove('comments-table-active');
            })

            if (loaded_tables[direction.id][0] == 0){
                comments_table_builder.loadComments(loaded_tables[direction.id][1])
            }
            direction.classList.add('comments-table-active');
        })
    })
}

function activateLoadMoreCommentsButtons(){
    $('#load-more-unseen-comments-button').on('click', ()=>{
        comments_table_builder.loadComments('unseen')
    })

    $('#load-more-seen-comments-button').on('click', ()=>{
        comments_table_builder.loadComments('seen')
    })

    $('#load-more-received-author-reply-comments-button').on('click', ()=>{
        comments_table_builder.loadComments('replied')
    })

    $('#load-more-banned-comments-button').on('click', ()=>{
        comments_table_builder.loadComments('banned')
    })
}

function loadCommentsPage(){
    linkNavTabsToTables()

    activateLoadMoreCommentsButtons()

    comments_table_builder.loadComments('unseen')
}

function changeWidth(){
    const tab = document.getElementById('commentaries')
    tab.style.width = `${tab.style.width-200}`
}

const comments_table_builder = new CommentsTableBuilder()

$('#reply-dialog-close-reply-dialog-button').on('click', ()=>{
    document.querySelector('#reply-dialog-textarea').value = ''
    document.querySelector('#reply-dialog').close()
})

$('#ban-comment-dialog-close-ban-comment-dialog-button').on('click', ()=>{
    document.querySelector('#ban-comment-dialog-textarea').value = ''
    document.querySelector('#ban-comment-dialog').close()
})

$('#reply-dialog-textarea').on('input', resizeTextArea)
    

const table_tabs = document.querySelectorAll('.comments-table-tab')

const table_nav_tabs = document.querySelectorAll('.comments-table-direction')

const loaded_tables = {
    'unseen-comments-tables-div': [1, 'unseen'], 
    'seen-comments-tables-div': [0, 'seen'], 
    'received-author-reply-comments-tables-div': [0, 'replied'], 
    'banned-comments-tables-div': [0, 'banned']}