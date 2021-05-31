import asyncio
from aiosfstream import SalesforceStreamingClient, RefreshTokenAuthenticator, Client
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, request, redirect, url_for
import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))    #Generate toekn
from json import loads
import requests
from urllib.parse import urlparse

CLIENT_SECRET = 'A53A18827957DE6C5828DB2A030E33592C560615EF70CD3568B1B8434A5C5876'
CLIENT_ID = '3MVG9d8..z.hDcPIXQrmkWobDdePFvV91zBoNNn6.u9PPoB_5eT9c8ZEbjrK2eSG6tC6dRpG7Efaqvut18CIO'
REDIRECT_URL = 'https://c79485f0e80e.ngrok.io/oauth2/callback'
RESPONSE_TYPE = 'code'

EVENT_NAME = ''

v_eventName = ""

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) #Generating the secret key
socketio = SocketIO(app, engineio_logger=True, logger=True, cors_allowed_origins='https://c79485f0e80e.ngrok.io', async_mode="threading")

@app.route('/', methods=['POST', 'GET'])
def home():
    authUrl = 'client_id='+CLIENT_ID
    authUrl = authUrl + '&redirect_uri='+REDIRECT_URL
    authUrl = authUrl + '&response_type='+RESPONSE_TYPE+'&prompt=login'
    authUrlProd = 'https://login.salesforce.com/services/oauth2/authorize?'+authUrl
    authUrlSand = 'https://test.salesforce.com/services/oauth2/authorize?'+authUrl
    print(authUrl)
    return render_template("index.html", token='', actionUrlProd=authUrlProd, actionUrlSand=authUrlSand)


@app.route('/oauth2/callback', methods=['POST', 'GET'])
def oauthCallback():
    print('code-->'+request.args.get('code'))
    print('urlDomain==>'+str(urlparse(request.url)))
    print('urlDomain==>'+urlparse(request.url_root).netloc)
    global domain
    domain = urlparse(request.url_root).netloc

    authDetails = getAccessToke( request.args.get('code') )
    if( authDetails != None or authDetails['refresh_token'] != None ):
        global REFRESH_TOKEN, ORG_URL
        REFRESH_TOKEN = authDetails['refresh_token']
        ORG_URL = urlparse(authDetails['instance_url']).netloc
    else:
        return render_template( 'error.html' )
    
    print('RefershToke1--->'+REFRESH_TOKEN)
    return render_template( 'redirectingTemp.html' )
    ##return redirect(url_for('getPEDetails'), code=authCode)


@app.route('/getOrgType', methods=['POST', 'GET'])
def getOrgType():
    print('orgType--->'+request.form.get('OrgType'))
    global orgDomain
    if( request.form.get('OrgType') == 'sandbox' ):
        orgDomain = 'test.salesforce.com'
    else:
        orgDomain = 'login.salesforce.com'
    return None


@app.route('/subscribeToPE', methods=['POST', 'GET'])
def getPEDetails():
    PEObjName = None
    if( request.form.get('peName') != None ):
        PEObjName = request.form.get('peName')
        print( 'object-->'+PEObjName )
        print('refreshToken3-->'+REFRESH_TOKEN)
        EVENT_NAME = PEObjName
        subscribePlatformEvent()

    return render_template("EventSubscription.html", PEObjName=PEObjName, org_name=ORG_URL )


def messageReceived(methods=['GET', 'POST']):
    print('Hey Yaaa')


# @socketio.on('my event')
# def handle_my_custom_event(json, methods=['GET', 'POST']):
#     print('received my event: ' + str(json))
#     socketio.emit('my response', json, callback=messageReceived)


@socketio.on('my event')
def stream_events(eventDetails, methods=['GET', 'POST']):
    print('RefreshToke-->'+REFRESH_TOKEN)
    print('clientsec-->'+CLIENT_SECRET)
    print('clientsec-->'+CLIENT_ID)
    print('json-->'+str(eventDetails))

    loop = asyncio.new_event_loop()
    loop.run_until_complete(perform_message( eventDetails['evtname'] ))


async def perform_message( eventName ):
    ##message = ws.receive()
    v_ptfevt = "/event/"+eventName
    isSandbox = False
    if( 'test.salesforce' in orgDomain ):
        isSandbox = True

    auth = RefreshTokenAuthenticator(
            consumer_key=CLIENT_ID,
            consumer_secret=CLIENT_SECRET,
            refresh_token=REFRESH_TOKEN,
            sandbox=isSandbox
        )
    client = Client(auth)

    await client.open()
        # subscribe to topics
    print("Connexion successful to the org!")
    print("Subscribing to the Platform Event...")
    await client.subscribe(v_ptfevt)

    print("Subscribed successfully to the event!")
    print("Listening for incoming messages...")
    socketio.emit('my response', {'data':{'message':'Listening To PE Events'}}, callback=messageReceived)
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
    authURL = 'https://'+orgDomain+'/services/oauth2/token?'
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