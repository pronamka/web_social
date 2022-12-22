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
    console.log(resp)
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


var load_on_scroll = function(event) {
    
    if ((window.innerHeight+window.scrollY) >= document.body.offsetHeight-200){
        console.log('called')
        getPosts(2);
    } }
document.addEventListener("scroll", throttle(load_on_scroll, 100));