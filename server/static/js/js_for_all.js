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

String.prototype.format = function () {
  var i = 0, args = arguments;
  return this.replace(/{}/g, function () {
    return typeof args[i] != 'undefined' ? args[i++] : '';
  });
};


class StringConstants{
  get articleFilePath(){
    return 'static/upload_folder/articles/{}.pdf'
  }
  get previewFilePath(){
    return 'static/upload_folder/previews/{}.jpeg'
  }
}

function getTemplate(template_identifier){
  return templates.content.querySelector(template_identifier).cloneNode(true)
}



function sendRequest(method, url, body) {
  //function for sending json via `POST` requests
  //WARNING: though the request method could be specified,
  //it will always have `{'Content-Type': 'application/json'}` as
  //the header (multipart data should not be sent by this function 
  //and if the request method is `GET`, then the view on the server
  //side must accept `POST` requests anyways.)

  const headers = {'Content-Type': 'application/json'}
  return fetch(url, {
      method: method,
      body: JSON.stringify(body),
      headers: headers}).then(response => {
      return response.text();
  })
}


function insertHTML(direction, html) {
  const tab = document.querySelector(direction);
  var template = document.createElement('template');
  html = html.trim(); // Never return a text node of whitespace as the result
  template.innerHTML = html;
  tab.appendChild(template.content);
  return template.content.firstChild;
}

function insertNode(direction, node){
  document.querySelector(direction).appendChild(node)
}


function loadAvatar(){
  sendRequest('POST', '/load_info/', {'page': 'personal_data'}).then(
    resp =>{document.getElementById('user_avatar_pic_img').innerHTML = 
    `<img src="${JSON.parse(resp)['avatar']}" class="avatar"></img>`
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

function resizeTextArea(){
  this.style.height = 0;
  this.style.height = this.scrollHeight + 'px'
}

function closeDialog(){
  this.close()
}

function loadOnScroll(event){
  if (load_on_scroll_disabled == true){
    return 0;
  }
  if ((window.innerHeight+window.scrollY) >= document.body.offsetHeight-200){
    try{
      getPosts(2);
    }
    catch{
      local_post_loading_function()
    }
  }
}


let templates = ''
fetch('http://192.168.0.249:4000/static/js/dev_studio/templates.html', {method: 'GET'}).then(
  resp=>{return resp.text()}).then(
    resp=>{
      templates = document.createElement('template')
      templates.innerHTML = resp
    })

const stringConstants = new StringConstants()
var load_on_scroll_disabled = false
var with_avatar = true

document.addEventListener("scroll", throttle(loadOnScroll, 100));

document.addEventListener('DOMContentLoaded', ()=>{
  if (with_avatar === false){
    return
  }
  loadAvatar()
})
