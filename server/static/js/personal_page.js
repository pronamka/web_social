
function sendAvatar(){
    const file_data = document.getElementById('avatar_file').files[0]
    const file = new FormData()
    file.append('file', file_data)
    file.append('filename', file_data[name])
    fetch('/change_avatar/', {method: 'POST', body: file, headers: {'Accept': 'appliction/json'}}).then(resp => {
        if (resp.status === 200){
            alert('Avatar Changed', window.location.reload())
        }
        else{
            alert('Something went wrong!')
        }
    })
}


function loadPersonalData(){
    sendRequest('POST', url, {'page': 'personal_data'}).then(resp => {
        user_current_interests = JSON.parse(resp)['interests']
        article_tags_manager.tags = user_current_interests
        article_tags_manager.tags_plain = flatten_dict(user_current_interests)
        var avatar = document.getElementById('avatar')
        avatar.innerHTML = `<img src=${JSON.parse(resp)['avatar']}>`
        insertHTML('#interests_list', displayInterests(user_current_interests))
    })
}


function sendInterestsChanges(){
    sendRequest('POST', '/change_interests/', {'interests': article_tags_manager.tags}).then(resp => {
        window.location.reload()
    })
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
    var mark = `<p onclick="changeStatus('${interest}')" 
    id="interest-status-mark ${interest}" class='interest-status-mark'>`
    if (interest in interests_plain){
        var index = 'class="interests selected"'
        mark += '&#x2713;'
    }
    else if(!(interest in interests_plain)){
        var index = 'class="interests unselected"'
        mark += '&#x2717;'
    }
    mark += '</p>'
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
        onhover = `onmouseenter="showScienceDescription('${summary_name}')" onmouseleave="hideScienceDescription('${summary_name}')"`
    }
    html = `<details id="details ${summary_name}"><summary id="${summary_name}" 
        ${summary_index[0]} child_of="${child_of}" ${onhover}>
        ${summary_name}${summary_index[1]}</summary><ul>`
    for (const key in interests){
        if (Object.keys(interests[key]).length == 0){
            var index, mark = ''
            var onmouseover = ''
            if (with_indexing){
                var i_m = getIndex(key)
                index = i_m[0]
                mark = i_m[1]
                onmouseover = `onmouseenter="showScienceDescription('${key}')"
                 onmouseleave="hideScienceDescription('${key}')"`
            }
            if (add_to_chosen){
                interests_plain[key] = {}
            }
            html += `<li id="${key}" ${index} child_of="${summary_name}" ${onmouseover}>
            ${key}${mark}</li>`
        }
        else if(typeof interests[key] == 'object'){
            if (with_indexing){
                summary_index = getIndex(key)
            }
            if (add_to_chosen){
                interests_plain[key] = {}
            }
            html += displayInterests(interests[key], key, with_indexing, add_to_chosen, summary_index, summary_name)
        }
    }
    html += `</ul></details>`
    return html
}

function chooseInterest(){
    loadAllInterests()
    document.getElementById('manage_interests_dlg').showModal()
}

function loadAllInterests(){
    sendRequest('POST', '/load_info/', {'page': 'personal_data', 'all_interests': true}).then(resp => {
        var interests_and_descriptions = JSON.parse(resp)['interests']
        html = displayInterests(interests_and_descriptions['interests'], 'All interests', true, false)
        sciences_descriptions = interests_and_descriptions['descriptions']
        insertHTML('#all_interests', html)
    })    
}




/* Avatar dialog */
function displayFilename(){
    var file_input = document.getElementById('avatar_file').files
    if (file_input.length == 0){
        document.getElementById('new-avatar-filename').innerText = 'No file selected'
        return 0
    }
    document.getElementById('new-avatar-filename').innerText = file_input[0].name
}




const url = '/load_info/'

var user_current_interests = {}

var interests_plain = {}

var sciences_descriptions = {}

const article_tags_manager = new ArticleTagsManager()

const science_description_field = document.getElementById('science-description')

document.addEventListener('DOMContentLoaded', loadPersonalData)