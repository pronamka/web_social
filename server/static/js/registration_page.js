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


function sendData(){
    const login = document.getElementById('login').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;


    if (login == '' | email == '' | password == ''){
        document.getElementById('validation-errors-info').innerHTML='Please, fill in all the fields.';
        return false;
    }

    else{
        sendRequest('POST', '/register/', 
        {'login': login, 'password': password, 'email': email}).then(resp =>{
            const response = JSON.parse(resp)
            const status = response['status']
            if (status != 300){
                document.getElementById('validation-errors-info').innerHTML=response['error'];
            }
            else if (status == 300) {
                alert('We have sent a confirmation email to you. Please, check it.');
                window.location.replace(response['redirect'])
            }
        })
    }
}


$('#create-account-button').on('click', sendData)