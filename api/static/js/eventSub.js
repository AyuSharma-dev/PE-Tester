// var socket = io.connect('https://pe-tester.herokuapp.com/');

var headersDone = false;
document.body.style.zoom = 1.0;
var clientKey;
function showMore() {

    document.getElementById('showMore').style.display = 'none';
    document.getElementById('errorDetails').style.display = 'block';
}


var form = $('form').on('submit', function (e) {
    e.preventDefault()
    document.getElementById('customers').innerHTML = '';
    document.getElementById('showMore').style.display = 'none';
    document.getElementById('errorDetails').style.display = 'none';
    document.getElementById('refreshButton').style.display = 'none';
    document.getElementById('buttonHelpText').style.display = 'none';

    headersDone = false;
    document.getElementById('loader').style.display = 'block';
    document.getElementById('eventText').disabled = true;
    document.getElementById('submitBtn').disabled = true;
    document.getElementById('message_holder').innerHTML = '';

    if( clientKey == undefined ){
        clientKey = (Math.random() + 1).toString(36).substring(2);
    }

    var form = $(this);
    var url = '/eventDetails';
    var details = { eventType : $("#channelType").val(), eventName: $("#eventText").val(), clientKey: clientKey};

    $.ajax({
        type: "POST",
        url: url,
        data: JSON.stringify(details),
        contentType: "application/json",
        dataType: 'json',
        error: function(XMLHttpRequest, textStatus, errorThrown) { 
            afterProcess();
            document.getElementById('message_holder').innerHTML = '';
            $('span.message_holder').append('Something went wrong.');
            document.getElementById('showMore').style.display = 'block';
            document.getElementById('message_holder').style.fontSize = '200%';
            document.getElementById('refreshButton').style.display = 'none';
            document.getElementById('buttonHelpText').style.display = 'none';
            document.getElementById('errorDetails').innerHTML = textStatus+'-'+'Please subscribe to event again.';
        }
    });

    setTimeout(() => {
        afterProcess();
        $('span.message_holder').append('Listening To Events');
        //$('span.message_holder').append(document.getElementById('refreshButton'));
        document.getElementById('refreshButton').style.display = 'inline-block';
        document.getElementById('buttonHelpText').style.display = 'inline-block';
        
    }, 3000);
    $('input.message').val('').focus()
})


function afterProcess(){
    document.getElementById('loader').style.display = 'none';
    document.getElementById('eventText').disabled = false;
    document.getElementById('submitBtn').disabled = false;

    document.getElementById('eventSubHtml').style.height = '190%';
    window.scrollTo(0, 2000);
    document.getElementById('message_holder').style.fontSize = '250%';
}


function getReceivedEvents(){

    document.getElementById("refreshButton").disabled = true;
    document.getElementById("refreshButton").style.background = '#a4b7c8';
    setTimeout(function(){
        document.getElementById("refreshButton").disabled = false;
        document.getElementById("refreshButton").style.background = '#02315b';
    },3000);

    $.ajax({
        type: "GET",
        url: 'getReceivedDetails',
        data: { clientKey: clientKey },
        success: function (data) {
            headersDone = false;
            data = JSON.parse(data);
            document.getElementById('customers').innerHTML = '';
            if( data && data.length > 0 ){
                var tableData = '';
                for( let i=0; i<data.length; i++ ){
                    if (!headersDone) {
                        window.scrollTo(0, 10000);
                        tableData += '<tr>';
                        for (var key in data[i]) {
                            tableData += '<th>' + key + '</th>'
                        }
                        headersDone = true;
                        tableData += '</tr>';
                    }
                    tableData += '<tr>';
                    for (var key in data[i]) {
                        tableData += '<td>' + data[i][key] + '</td>'
                    }
                    tableData += '</tr>';
                }
                $('table.event_data').append(tableData)
            }
        }
    });
}