

function verifyPost(post_id){
    sendRequest('POST', '/admin/verify_post/', {'post_id': post_id}).then(resp => respond(resp, 'verified'))
}

function banPost(post_id){
    problem_description = document.getElementById('problem-description-textarea').value
    if (problem_description.length > 0){
        sendRequest('POST', '/admin/ban_post/', {'post_id': post_id, 
        'problem_description': problem_description}).then(resp => respond(resp, 'banned'))
    }
    else{
        alert('Please, describe why do you want to ban the post.')
    }
}

function respond(status_message, action){
    console.log(status_message)
    debugger
    const status = JSON.parse(status_message)['status']
    if (status == 'successful') {
        document.getElementById('ban-post-button').disabled = true
        document.getElementById('verify-post-button').disabled = true
        alert('Post '+ action +' successfully.')
    }
    else {
        var message = document.createElement('p')
        message.appendChild(document.createTextNode(`The post was not `+ action +` because an error
            occured on the server side: `+ status +`. Please, 
            contact our technical support at defender0508@gmail.com.`))
        warning_dialog.appendChild(message)
        warning_dialog.showModal()
    }
}

$('#problem-description-textarea').on('input', resizeTextArea)

with_avatar = false