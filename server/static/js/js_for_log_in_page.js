const already_logged_in_dlg = document.getElementById('change_session_dlg')

const restore_password_dlg = document.getElementById('restore_password_dlg')
const errors_message = document.getElementById('error')
const email_inp = document.getElementById('email')
const restore_by_login_inp = document.getElementById('restore_by_login')

const login_inp = document.getElementById('login')
const password_inp = document.getElementById('password')

const validation_errors = document.getElementById('validation_errors')

const credentials = {'login': null, 'password': null}

function sendRequest(method, url, body) {
    const headers = {'Content-Type': 'application/json'}
    return fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: headers}).then(response => {
        return response.text()
    })
}
function showRestorePasswordDialog(){
    restore_password_dlg.showModal()
}
function restore(){
    var email_address = email_inp.value
    var login = restore_by_login_inp.value
    sendRequest('POST', '/restore_password/', 
    {'email_address': email_address, 'login': login}).then(resp=>{
        const response = JSON.parse(resp)
        if (response['status'] == 200){
            alert('We have sent an email to the given email address.')
            errors_message.innerText = ''
            restore_password_dlg.close()
        }
        else{
            errors_message.innerText = response['response']
        }
    })
}
function logIn(){
    if (checkInputs() == false){
        return null
    }
    credentials['login'] = login_inp.value
    credentials['password'] = password_inp.value
    sendRequest('POST', '/log_in/', credentials).then(resp=>{
        response = JSON.parse(resp)
        var status = response['status']
        var message = response['response']
        if (status == 300){
            window.location.replace(message)
        }
        else if (status == 406){
            validation_errors.innerHTML = 'Wrong credentials.'
        }
        else if (status == 409){
            document.getElementById('warning_message').innerHTML = "You are already logged in as "+ response['logged_as'] +" <br>Log in anyways? (Your previous session will be closed)"
            already_logged_in_dlg.showModal()
        }
        else if (status == 412){
            validation_errors.innerText = 'You did not confirm your email.'
        }
    })
}
function changeSession(){
    sendRequest('POST', '/log_in_anyways/', credentials).then(resp=>{
        window.location.replace(JSON.parse(resp)['response'])
    })
}

function checkInputs(){
    if (login == '' | password == ''){
        document.getElementById('validation_errors').innerHTML='Please, fill in all the fields.';
        return false;
    }
    else{
        return true;
    }
}

function cancel(dialog_id) {
    document.getElementById(dialog_id).close()
}