
class HubBuilder{
    constructor(content_for_hub){
        this.content_for_hub = content_for_hub;
        this.latest_post_html = '';
        this.short_analytics_html = '';
    }

    buildHub(){
        //Constructs the html code that should be inserted into the document.
        //Does not insert the html, for that use `.insertIntoDocument` method.
        if (this.content_for_hub['latest_posts'] != 0){
            this.buildLastPostDisplay();
            this.buildLastPostInformation();
        }
        else{
            this.buildNoPostDummy();
        }
        this.buildShortAnalytics();
    }

    buildLastPostDisplay(){
        const path = `/static/upload_folder/articles/${
            this.content_for_hub['latest_posts']['0']['post_id']}.pdf`;
        const title = this.content_for_hub['latest_posts']['0']['title']
        this.latest_post_html += 
        `<div id="latest-post-wrapper">
            <h3 id='latest-post-title'>${title}</h3>
            <iframe src="${path}" id="latest-post-iframe"></iframe>
        </div>`;
    }

    buildLastPostInformation(){

        const post = this.content_for_hub['latest_posts']['0'];
        this.latest_post_html += 
        `<div id="latest-post-info-wrapper">
            <h3 id='last-post-short-info-header'>${post['title']} short analytics:</h3>
            <p class='last-post-info'><em id='post-made-ago'>${post['made_ago_str']}<em></p>
            <p class='last-post-info'>Views: ${post['views_amount']}</p>
            <p class='last-post-info'>Likes: ${post['likes_amount']}</p>
            <p class='last-post-info'>Comments: ${this.content_for_hub['commentaries_received']}</p>
        </div>`;
    }

    buildNoPostDummy(){
        this.latest_post_html += 
        `<div id="no-posts-yet-wrapper">
            <img src="/static/images/no_posts_yet.jpg" id='no-posts-image'>
            <p id='no-posts-yet-info'>
                You have not made any publications yet.
                Click the button below to start!
            </p>
            <button onclick="showUploadDialog();" id="make-first-post-button">
                Upload an article
            </button>
        </div>`;
    }

    buildShortAnalytics(){
        const overall_post_statistics = this.content_for_hub['overall_user_post_statistics']
        this.short_analytics_html = 
        `<div id='overall-information'>
            <h3 id='account-analytics-header'>Account analytics</h3>
            <p class='account-overall-info' id='subscribers-amount-wrapper'>Subscribers
            <p id='subscribers-amount'>${this.content_for_hub['subscribers']}</p>
            </p>
            <div class='splitline'></div>
            <h3 id='all-time-statistics-header'>Statistics For All Time</h3>
            <div id='account-overall-info-grid'>
                <p class='account-overall-info'>Publications</p><div class="account-statistics-number">${this.content_for_hub['post_amount']}</div>
                <p class='account-overall-info'>Views</p><div class="account-statistics-number">${overall_post_statistics['views'] || 0}</div>
                <p class='account-overall-info'>Likes</p><div class="account-statistics-number">${overall_post_statistics['likes'] || 0}</div>
                <p class='account-overall-info'>Comments</p><div class="account-statistics-number">${overall_post_statistics['comments'] || 0}</div>
            </div>
        </div>`;
    }

    insertIntoDocument(){
        insertHTML('#last_post', this.latest_post_html);
        insertHTML('#short_analytics', this.short_analytics_html);
    }
}


function loadHub(){
    sendRequest('POST', '/load_info/', {'page': 'hub', 'posts_required': 1, 'posts_loaded': 0, 
    'of_user': true, 'post_type': 2}).then(resp => {
        const content = JSON.parse(resp)
        const hub_builder = new HubBuilder(content)
        hub_builder.buildHub()
        hub_builder.insertIntoDocument()
    })
}

class ArticleUploadManager{
    constructor(){
        this.article_data = document.getElementById('inp-file-content').files[0]
        this.preview_data = document.getElementById('upload-article-dialog-upload-article-preview-input').files[0]
        this.file_article = new FormData()
    }

    fillFile(){
        this.file_article.append('article', this.article_data)
        this.file_article.append('article_filename', this.article_data['name'])
        this.file_article.append('tags', JSON.stringify(article_tags_manager.tags))
    }

    fillPreview(){
        this.file_article.append('preview', this.preview_data)
        this.file_article.append('previw_filename', this.preview_data['name'])
    }

    sendArticle(){
        fetch('/upload_file/', {method: 'POST', body: this.file_article, 
        headers: {'Accept': 'application/json'}}).then(response=>response.text()).then(resp=>{
            alert(resp, window.location.reload())
        })
    }
}


function showUploadDialog () {
    const upload_dialog = document.querySelector('#upload_article_dlg');
    upload_dialog.showModal()
}

function uploadArticle(){
    const manager = new ArticleUploadManager()
    manager.fillFile()
    manager.fillPreview()
    manager.sendArticle()
}




function getParent(key, action=false){
    var elem = document.getElementById(key)
    if (action){
        elem.style.backgroundColor = 'lightgreen'
        elem.setAttribute('class', 'interests selected')
        document.getElementById(`interest-status-mark ${key}`).innerHTML = '&#x2713;'
    }
    var child_of = elem.getAttribute('child_of')
    return child_of
}

function getFullInheritanceTree(key, action=false){

    var tree = {}
    tree[key] = {}
    while (true){
        parent = getParent(key, action)
        if (parent=='All interests'){
            return tree;
        }
        var temp = {}
        temp[parent] = tree
        tree = temp
        key = parent
    }
}

function flatten_dict(interest_tree_dict){
    var result = {}
    for (const i in interest_tree_dict){
        result[i] = {}
        if (interest_tree_dict[i].length != 0){
            result = Object.assign({}, result, flatten_dict(interest_tree_dict[i]))
        }
    }
    return result
}

class ArticleTagsManager{
    constructor(){
        this.tags_plain = {}
        this.tags = {}
    }

    changeTagStatus(key){
        this.keepDetailsUntouched(key)
        const elem = document.getElementById(key)
        const mark = document.getElementById(`interest-status-mark ${key}`)
        if (key in this.tags_plain){
            //if the key is already in the plain representation of
            //the chosen tags, then the science was selected earlier
            //and so the user wants to unselect it.
            const tree = getFullInheritanceTree(key)
            this.unselectChildren(key)
            this.tags = this.removeTag(tree, this.tags)
            elem.setAttribute('class', 'interests unselected')
            elem.style.backgroundColor = 'lightcoral'
            mark.innerHTML = '&#x2717;'
        }
        else{
            const tree = getFullInheritanceTree(key, true)
            this.tags = this.insertTag(tree, this.tags)
            this.tags_plain = Object.assign({}, this.tags_plain, flatten_dict(this.tags))
            elem.setAttribute('class', 'interests selected')
            mark.innerHTML = '&#x2713;'
        }
    }

    unselectChildren(key){
        var parent = document.getElementById(`details ${key}`)
        if (parent===null){
            return 0;
        }
        var elems = parent.getElementsByClassName('interests selected')
        for (var i=0; i<elems.length; i++){
            elems[i].style.backgroundColor = 'lightcoral'
            elems[i].getElementsByClassName('interest-status-mark')[0].innerHTML = '&#x2717;'
        }
    }

    insertTag(interest_tree, user_tree){
        var interest = Object.keys(interest_tree)[0]
        this.tags_plain[interest] = {}
        if (interest in user_tree){
            user_tree[interest] = this.insertTag(interest_tree[interest], user_tree[interest])
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

    removeTag(interest_tree, user_tree){
        var interest = Object.keys(interest_tree)[0]
        if (Object.keys(interest_tree[interest]).length != 0){
            user_tree[interest] = this.removeTag(interest_tree[interest], user_tree[interest])
            return user_tree
        }
        else{
            var s = flatten_dict(user_tree[interest])
            for (const i in s){
                delete this.tags_plain[i]
            }
            delete user_tree[interest]
            delete this.tags_plain[interest]
            return user_tree
        }
    } 

    keepDetailsUntouched(key){
        //when the user click the mark in the summary to select/unselect
        //a tag, details shoud not be opened or closed, so the details state
        //is kept untouched
        var details = document.getElementById(`details ${key}`)
        if (details){
            if (details.open){
                details.open = false
            }
            else{
                details.open = true
            }
        }
    }
}

function changeStatus(key){
    article_tags_manager.changeTagStatus(key)
}

function getIndex(interest){
    var mark = `<p onclick="changeStatus('${interest}')" id="interest-status-mark ${interest}" class='interest-status-mark'>`
    var index = 'class="interests unselected"'
    mark += '&#x2717;</p>'
    return [index, mark]
}

function showScienceDescription(science_name){
    if (sciences_descriptions[science_name]){
        science_description_field.innerText = sciences_descriptions[science_name]
    }
}

function hideScienceDescription(science_name){
    science_description_field.innerText = 
    'A short description of a science will appear here when you hover over it.'
}


function displayInterests(interests, summary_name='Your interests', with_indexing=false, add_to_chosen=true, summary_index=['', ''], child_of=''){
    var onhover = ''
    if (with_indexing){
        onhover = `onmouseenter="showScienceDescription('${summary_name}')" 
        onmouseleave="hideScienceDescription('${summary_name}')"`
    }
    html = `<details id="details ${summary_name}"><summary id="${summary_name}" 
        ${summary_index[0]} child_of="${child_of}" ${onhover}>
        ${summary_name}${summary_index[1]}</summary><ul>`
    for (const key in interests){
        if (Object.keys(interests[key]).length == 0){
            var index_and_mark = getIndex(key)
            var onmouseover = `onmouseenter="showScienceDescription('${key}')"
                 onmouseleave="hideScienceDescription('${key}')"`
                 html += `<li id="${key}" ${index_and_mark[0]} child_of="${summary_name}" ${onmouseover}>
                 ${key}${index_and_mark[1]}</li>`
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
        resp = JSON.parse(resp)['interests']
        sciences_descriptions = resp['descriptions']

        html = displayInterests(resp['interests'], 'All interests', true, false)
        insertHTML('#all_interests', html)
    })    
}


function displayFilename(input_id='inp-file-content', label_id='article-filename'){
    var file_input = document.getElementById(input_id).files
    if (file_input.length == 0){
        document.getElementById(label_id).innerText = 'No file selected'
        return 0
    }
    document.getElementById(label_id).innerText = file_input[0].name
}


function getTemplate(template_identifier){
    const elem = $.get('/static/js/dev_studio/templates.html', null, function(text){
        return $(text).find(template_identifier);
    });
    return elem;
}


//buttons in the navigation menu that are used to change the content of the page
const nav_tabs = document.querySelectorAll('[data-tab-value]');

//tabs containing actual content. Current tab has style `active`
const tabs_content = document.querySelectorAll('[data-tab-info]');

//
var sciences_descriptions = {}

const science_description_field = document.getElementById('science-description')

//functions that need to be executed when the tab gets opened for the first time,
//to load the content, as it is not loaded all at once when loading the page
const action_protocols = {'hub': {'call': loadHub, 'called': 0}, 
                        'content': {'call': loadContentPage, 'called': 1}, 
                        'analytics': {'call': loadFirstChart, 'called': 0},
                        'commentaries': {'call': loadCommentsPage, 'called': 0}, 
                        'translations': {'call': 0, 'called': 1},
                        'copyright': {'call': 0, 'called': 1}, 
                        'monetization': {'call': 0, 'called': 1}};

//storage for tags when uploading a file
var article_upload_tags = {}

//representation of article tags without nesting
//(used to check if a tag is chosen or not)
var chosen_tags_plain = {}

const article_tags_manager = new ArticleTagsManager()

//hub is opened by default(it's the firt active tab)
document.addEventListener('DOMContentLoaded', loadContentPage);

document.addEventListener('DOMContentLoaded', loadAllInterests)

$('#inp-file-content').on('change', ()=>{
    displayFilename('inp-file-content', 'article-filename')
})

$('#upload-article-dialog-upload-article-preview-input').on('change', ()=>{
    displayFilename('upload-article-dialog-upload-article-preview-input', 'preview-filename')
})


//add an event listener for every tab button
nav_tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const direction = document.querySelector(tab.dataset.tabValue);
        tabs_content.forEach(tabInfo => {
            tabInfo.classList.remove('active');
        })
        const a = direction['id']
        if (action_protocols[a]['called'] == 0){
            action_protocols[a]['call']()
            action_protocols[a]['called'] = 1
        }
        direction.classList.add('active');
    })
})
