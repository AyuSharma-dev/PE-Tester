var socket = io.connect('https://' + document.domain + ':' + location.port, {
    secure: false
});
var headersDone = false;
document.body.style.zoom = 1.0;

function showMore() {

    document.getElementById('showMore').style.display = 'none';
    document.getElementById('errorDetails').style.display = 'block';
}

socket.on('connect', function () {
    var form = $('form').on('submit', function (e) {
        e.preventDefault()
        document.getElementById('customers').innerHTML = '';
        document.getElementById('showMore').style.display = 'none';
        document.getElementById('errorDetails').style.display = 'none';
        headersDone = false;
        document.getElementById('loader').style.display = 'block';
        document.getElementById('eventText').disabled = true;
        document.getElementById('submitBtn').disabled = true;
        document.getElementById('message_holder').innerHTML = '';

        let eventName = $('input.evtname').val()
        socket.emit('eventToSubscribe', {
            evtname: eventName
        })
        $('input.message').val('').focus()
    })
})
socket.on('receivedEvent', function (msg) {
    console.log('msg-->' + JSON.stringify(msg));
    document.getElementById('loader').style.display = 'none';
    document.getElementById('eventText').disabled = false;
    document.getElementById('submitBtn').disabled = false;

    if( msg.data != undefined ){
        if( msg.data.error !== undefined ){
            $('div.message_holder').append(msg.data.message)
            document.getElementById('showMore').style.display = 'block';
            document.getElementById('message_holder').style.fontSize = '200%';
            document.getElementById('errorDetails').innerHTML = msg.data.error;
        }
        else if (msg.data.message !== undefined) {
            document.getElementById('eventSubHtml').style.height = '190%';
            window.scrollTo(0, 2000);
            document.getElementById('message_holder').style.fontSize = '250%';
            $('div.message_holder').append(msg.data.message)
        } else{
            var tableData = '';
            if (!headersDone) {
                window.scrollTo(0, 10000);
                tableData += '<tr>';
                for (var key in msg.data) {
                    tableData += '<th>' + key + '</th>'
                }
                headersDone = true;
                tableData += '</tr>';
            }
            tableData += '<tr>';
            for (var key in msg.data) {
                tableData += '<td>' + msg.data[key] + '</td>'
            }
            tableData += '</tr>';
    
            $('table.event_data').append(tableData)
        }
    }
})