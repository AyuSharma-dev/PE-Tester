import asyncio
from aiosfstream import SalesforceStreamingClient, RefreshTokenAuthenticator, Client
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, request, redirect, url_for
import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))    #Generate toekn
from json import loads
import requests

CLIENT_SECRET = 'A53A18827957DE6C5828DB2A030E33592C560615EF70CD3568B1B8434A5C5876'
CLIENT_ID = '3MVG9d8..z.hDcPIXQrmkWobDdePFvV91zBoNNn6.u9PPoB_5eT9c8ZEbjrK2eSG6tC6dRpG7Efaqvut18CIO'
REDIRECT_URL = 'https://0a44042e19dd.ngrok.io/oauth2/callback'
RESPONSE_TYPE = 'code'
EVENT_NAME = ''

v_eventName = ""

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) #Generating the secret key
socketio = SocketIO(app, engineio_logger=True, logger=True, cors_allowed_origins='https://0a44042e19dd.ngrok.io', async_mode="threading")

@app.route('/', methods=['POST', 'GET'])
def home():
    authUrl = 'https://login.salesforce.com/services/oauth2/authorize?'
    authUrl = authUrl + 'client_id='+CLIENT_ID
    authUrl = authUrl + '&redirect_uri='+REDIRECT_URL
    authUrl = authUrl + '&response_type='+RESPONSE_TYPE
    print(authUrl)
    return render_template("index.html", token='', actionUrl=authUrl)


@app.route('/oauth2/callback', methods=['POST', 'GET'])
def oauthCallback():
    print('code-->'+request.args.get('code'))
    authDetails = getAccessToke( request.args.get('code') )
    if( authDetails != None or authDetails['refresh_token'] != None ):
        global REFRESH_TOKEN
        REFRESH_TOKEN = authDetails['refresh_token']
    else:
        return render_template( 'error.html' )
    
    print('RefershToke1--->'+REFRESH_TOKEN)
    return render_template( 'redirectingTemp.html' )
    ##return redirect(url_for('getPEDetails'), code=authCode)


@app.route('/subscribeToPE', methods=['POST', 'GET'])
def getPEDetails():
    PEObjName = None
    if( request.form.get('peName') != None ):
        PEObjName = request.form.get('peName')
        print( 'object-->'+PEObjName )
        print('refreshToken3-->'+REFRESH_TOKEN)
        EVENT_NAME = PEObjName
        subscribePlatformEvent()

    return render_template("EventSubscription.html", PEObjName=PEObjName, peData=None)


def messageReceived(methods=['GET', 'POST']):
    print('Hey Yaaa')


# @socketio.on('my event')
# def handle_my_custom_event(json, methods=['GET', 'POST']):
#     print('received my event: ' + str(json))
#     socketio.emit('my response', json, callback=messageReceived)


@socketio.on('my event')
def stream_events(json, methods=['GET', 'POST']):
    print('RefreshToke-->'+REFRESH_TOKEN)
    print('clientsec-->'+CLIENT_SECRET)
    print('clientsec-->'+CLIENT_ID)

    loop = asyncio.new_event_loop()
    loop.run_until_complete(perform_message())


async def perform_message():
    ##message = ws.receive()
    v_ptfevt = "/event/"+'Notification__e'

    auth = RefreshTokenAuthenticator(
            consumer_key=CLIENT_ID,
            consumer_secret=CLIENT_SECRET,
            refresh_token=REFRESH_TOKEN
        )
    client = Client(auth)

    await client.open()
        # subscribe to topics
    print("Connexion successful to the org!")
    print("Subscribing to the Platform Event...")
    await client.subscribe(v_ptfevt)

    print("Subscribed successfully to the event!")
    print("Listening for incoming messages...")
    socketio.emit('my response', {'data':{'message':'Listening To PE Events0'}}, callback=messageReceived)
    # listen for incoming messages
    async for message in client:
        topic = message["channel"]
        data = message["data"]
        payload = message["data"]["payload"]
        print(f"Payload is: {payload}")
        socketio.emit('my response', {'data':payload}, callback=messageReceived)


def subscribePlatformEvent():
    try:
        print('AAA')
    except KeyboardInterrupt:
        print()
        print()
        print("...Stopping the listener...")
        if v_eventName != "":
            client.unsubscribe(v_ptfevt)
        print("*************************************************************")
        print("Thanks for using our Platform Event listener, enjoy your day!")


def getAccessToke( code ):
    authURL = 'https://login.salesforce.com/services/oauth2/token?'
    authURL += 'grant_type=authorization_code&'
    authURL += 'code='+code
    authURL += '&client_id='+CLIENT_ID
    authURL += '&client_secret='+CLIENT_SECRET
    authURL += '&redirect_uri='+REDIRECT_URL
    req = requests.post( authURL )
    reqResult = loads(req.content)
    print('***response:'+str(reqResult))
    return reqResult

##Running the app
if __name__ == '__main__':
    socketio.run(app)
            
# if __name__ == "__main__":
#     try:
#         loop = asyncio.get_event_loop()
#         loop.run_until_complete(stream_events())
#     except KeyboardInterrupt:
#         print()
#         print()
#         print("...Stopping the listener...")
#         if v_eventName != "":
#             client.unsubscribe(v_ptfevt)
#         print("*************************************************************")
#         print("Thanks for using our Platform Event listener, enjoy your day!")