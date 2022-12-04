document.addEventListener('DOMContentLoaded', loadAvatar())
function sendRequest(method, url, body) {
    const headers = {'Content-Type': 'application/json'}
    console.log(body)
    return fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: headers}).then(response => {
        return response.text()
    })
}
function loadAvatar(){
    sendRequest('POST', '/load_info/', {'page': 'personal_data'}).then(resp =>{
        console.log(resp['avatar'])
        document.getElementById('user_avatar_pic_img').innerHTML = `<img src="${JSON.parse(resp)['avatar']}" class="avatar"></img>`
    })
}
function search(){
    var query = document.getElementById('search_query').value
    window.location.replace('/search_page?query='+query)
    
    `sendRequest('POST', '/search/', {'query': query}).then(resp=>{
        console.log(resp)
        status, response = JSON.parse(resp)
        console.log(window.location)
        if (status==300){
            window.location.replace(response)
        }
    })`
}


`current_position = 250
window.addEventListener("scroll", function(event) {
    var top = this.scrollY
    console.log(top, current_position)
    if (current_position < top){
        current_position += 1000
        getPosts();
    } 
}, false);`