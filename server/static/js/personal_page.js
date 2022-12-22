const url = '/load_info/'
var user_current_interests = ''
var interests_plain = {}
var sciences_descriptions = {}
const science_description_field = document.getElementById('science-description')
document.addEventListener('DOMContentLoaded', loadPersonalData())
function sendAvatar(){
    const file_data = document.getElementById('avatar_file').files[0]
    const file = new FormData()
    file.append('file', file_data)
    file.append('filename', file_data[name])
    fetch('/change_avatar/', {method: 'POST', body: file, headers: {'Accept': 'appliction/json'}}).then(resp => {
        alert(JSON.parse(resp), window.location.reload())
    })
}
function sendRequest(method, url, body) {
    const headers = {'Content-Type': 'application/json'}
    return fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: headers}).then(response => {
        return response.text()
    })
}
function loadPersonalData(){
    sendRequest('POST', url, {'page': 'personal_data'}).then(resp => {
        user_current_interests = JSON.parse(resp)['interests']
        var avatar = document.getElementById('avatar')
        console.log(resp)
        avatar.innerHTML = `<img src=${JSON.parse(resp)['avatar']}>`
        console.log(avatar)
        insertHTML(displayInterests(user_current_interests))
    })
}
function sendInterestsChanges(){
    sendRequest('POST', '/change_interests/', {'interests': user_current_interests}).then(resp => {
        window.location.reload()
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
function searchAndInsert(interest_tree, user_tree){
    var interest = Object.keys(interest_tree)[0]
    interests_plain[interest] = {}
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
function search(aim, tree){
    if (aim in tree){
        return tree[aim]
    }
    else{
        return search(aim, tree)
    }
}
function searchAndDelete(interest_tree, user_tree){
    var interest = Object.keys(interest_tree)[0]
    if (Object.keys(interest_tree[interest]).length != 0){
        user_tree[interest] = searchAndDelete(interest_tree[interest], user_tree[interest])
        return user_tree
    }
    else{
        var s = flatten(user_tree[interest])
        for (i in s){
            delete interests_plain[i]
        }
        delete user_tree[interest]
        delete interests_plain[interest]
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
    var tree = getFullInheritanceTree(key)
    var mark = document.getElementById(`interests_chosen_mark ${key}`)
    if (key in interests_plain) {
        user_current_interests = searchAndDelete(tree, user_current_interests)
        elem.setAttribute('class', 'interests unselected')
        mark.innerHTML = '&#x2717;'
    }
    else{
        user_current_interests = searchAndInsert(tree, user_current_interests)
        interests_plain = Object.assign({}, interests_plain, flatten(tree))
        console.log(user_current_interests)
        interests_plain[key] = {}
        elem.setAttribute('class', 'interests selected')
        mark.innerHTML = '&#x2713;'
    }
}
function getIndex(interest){
    var mark = `<p onclick="changeStatus('${interest}')" 
    id="interests_chosen_mark ${interest}" class='interest-status-mark'>`
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
    console.log(science_name)
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
function insertHTML(html, parent_node_id='interests_list'){
    const tab = document.getElementById(parent_node_id);
    var template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    tab.appendChild(template.content);
    return template.content.firstChild;
}
function chooseInterest(){
    loadAllInterests()
    document.getElementById('manage_interests_dlg').showModal()
}
function loadAllInterests(){
    sendRequest('POST', '/load_info/', {'page': 'personal_data', 'all_interests': true}).then(resp => {
        console.log(resp)
        var interests_and_descriptions = JSON.parse(resp)['interests']
        html = displayInterests(interests_and_descriptions['interests'], 'All interests', true, false)
        sciences_descriptions = interests_and_descriptions['descriptions']
        insertHTML(html, 'all_interests')
    })    
}

function displayFilename(){
    var file_input = document.getElementById('avatar_file').files
    if (file_input.length == 0){
        document.getElementById('new-avatar-filename').innerText = 'No file selected'
        return 0
    }
    document.getElementById('new-avatar-filename').innerText = file_input[0].name
}