function searchStrictly(query){
    var dialog = document.querySelector('#word-autocorrection-dialog')

    $(`#add-to-dictionary-and-search-button`).on('click', ()=>{
        window.location.replace(`/search_page?query=${query}&search_strictly=1&add_to_search=1`)
    })

    $('#search-strictly-without-adding-button').on('click', ()=>{
        window.location.replace(`/search_page?query=${query}&search_strictly=1`)
    })
    dialog.showModal()
}

function sendSearchRequest(){
    return sendRequest('POST', '/search/', settings).then(resp=>{
        var posts=JSON.parse(resp)
        settings['results_received'] += posts['search_results'].length
        if(posts['search_results'].length < settings['results_required']){
            document.getElementById('load-more-results-button').remove()
        }
        buildPosts(posts['search_results'])
        return posts
    })
}

    
function buildPosts(post_dict){
    for (var i=0, l=post_dict.length; i<l; i++){
        post = buildHTML(post_dict[i]);
        insertHTML('#search-results-wrapper', post);
    }
}

function buildPostTags(tags){
    html = ''
    for (var i=0; i<tags.length; i++){
        html+=`<li class='post-tag'>${tags[i]}</li>`
    }
    return html
}

function buildHTML(post){
    path = `/static/upload_folder/previews/${post['post_id']}.jpeg`
    html = `<div class="content-post-container">
                <iframe src="${path}" class='post-iframe'></iframe>
                <div class='content-post-info'>
                    <h3><a href='/view_post/?post_id=${post['post_id']}'>${post['title']}</a></h3>
                    <p>${post['made_ago_str']}</p>
                    <div class='content-post-info-grid'>
                        <p class='post-info'>Views</p><div class="post-info-number">${post['views_amount'] || 0}</div>
                        <p class='post-info'>Likes</p><div class="post-info-number">${post['like_amounts'] || 0}</div>
                        <p class='post-info'>Comments</p><div class="post-info-number">${post['comments_amount'] || 0}</div>
                    </div>
                    <div class='post-tags-wrapper'>
                        <details class='post-tags-details'>
                            <summary class='post-tags-summary'>
                                Post Tags
                            </summary>
                            <ul>
                                ${buildPostTags(post['tags_flattened'])}
                            </ul>
                        </details>
                    </div>
                </div>
            </div>`;
    return html
}

function loadSearchPage(){
    sendSearchRequest().then(resp=>{
        document.getElementById('loading-circle-wrapper').style.display = 'none'
        document.getElementById('search-page-container').style.display = 'block'

        if(resp['searched_for'] != settings['search_query']){
            document.querySelector('#autocorrected-request').innerHTML = `Showing results for ${resp['searched_for']}. 
            <a id="search-strictly-link">
                Search ${settings['search_query']}
            </a>`
            $(`#search-strictly-link`).on('click', ()=>{
                sendRequest(searchStrictly(settings['search_query']))
            })
        }

        if (resp['search_results'].length == 0){
            document.getElementById('no-results-wrapper').style.display = 'block'
        }
    
        $('#autocorrection-dialog-close-autocorrection-dialog-button').on('click', ()=>{
            document.getElementById('word-autocorrection-dialog').close()
        })
    })
}

local_post_loading_function = () =>{}

document.addEventListener('DOMContentLoaded', loadSearchPage)

$('#load-more-results-button').on('click', sendSearchRequest)
