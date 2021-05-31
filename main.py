import asyncio
from aiosfstream import SalesforceStreamingClient, RefreshTokenAuthenticator, Client
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, request, redirect, url_for
import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))    #Generate toekn
from json import loads
import requests
from urllib.parse import urlparse
import utility.constants as cons


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) #Generating the secret key
socketio = SocketIO(app, engineio_logger=True, logger=True, cors_allowed_origins=cons.DOMAIN, async_mode="threading")


@app.route('/', methods=['POST', 'GET'])
def home():
    authUrl = 'client_id='+cons.CLIENT_ID
    authUrl += '&redirect_uri='+cons.REDIRECT_URL
    authUrl += '&response_type='+cons.RESPONSE_TYPE#+'&prompt=login'
    authUrlProd = cons.PROD_URL+authUrl
    authUrlSand = cons.SANDBOX_URL+authUrl
    print(authUrl)
    return render_template("index.html", token='', actionUrlProd=authUrlProd, actionUrlSand=authUrlSand)


@app.route('/oauth2/callback', methods=['POST', 'GET'])
def oauthCallback():
    global domain
    domain = urlparse(request.url_root).netloc

    authDetails = getAccessToke( request.args.get('code') )
    if( authDetails != None or authDetails['refresh_token'] != None ):
        info.refresh_token = authDetails['refresh_token']
        info.org_url = urlparse(authDetails['instance_url']).netloc
    else:
        return render_template( 'error.html' )
    
    return render_template( 'redirectingTemp.html' )


@app.route('/getOrgType', methods=['POST', 'GET'])
def getOrgType():
    global orgDomain
    if( request.form.get('OrgType') == 'sandbox' ):
        orgDomain = cons.SANDBOX_DOMAIN
    else:
        orgDomain = cons.PROD_DOMAIN
    return render_template( 'EventSubscription.html' )


@app.route('/subscribeToPE', methods=['POST', 'GET'])
def getPEDetails():
    return render_template("EventSubscription.html", org_name=info.org_url )


@socketio.on('eventToSubscribe')
def stream_events(eventDetails, methods=['GET', 'POST']):
    
    try:
        if( info.loop is None ):
            info.loop = asyncio.new_event_loop()
            info.loop.run_until_complete(perform_message( eventDetails['evtname'] ))
        else:
            send_fut = asyncio.run_coroutine_threadsafe( perform_message( eventDetails['evtname'] ), info.loop)
    except Exception as e:
        socketio.emit('receivedEvent', {'data':{'error':str(e), 'message':'Sorry something went wrong!!'}}, callback=messageReceived)


def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')


async def perform_message( eventName ):
    global eventPath
    eventPath = "/event/"+eventName
    isSandbox = False
    if( info.client is None ):
        if( cons.SANDBOX_DOMAIN == orgDomain ):
            isSandbox = True

        auth = RefreshTokenAuthenticator(
                consumer_key=cons.CLIENT_ID,
                consumer_secret=cons.CLIENT_SECRET,
                refresh_token=info.refresh_token,
                sandbox=isSandbox
            )

        client = Client(auth)
        info.client = client

        await info.client.open()
    
    if( info.eventPath is None or (info.eventPath != eventPath) ):
        if( info.eventPath is not None and info.eventPath != eventPath ):
            await info.client.unsubscribe(info.eventPath)

        info.eventPath = eventPath
        await info.client.subscribe(eventPath)

        socketio.emit('receivedEvent', {'data':{'message':'Listening To PE Events'}}, callback=messageReceived)
        
        # listen for incoming messages
        async for message in info.client:
            topic = message["channel"]
            data = message["data"]
            payload = message["data"]["payload"]
            print(f"Payload is: {payload}")
            socketio.emit('receivedEvent', {'data':payload}, callback=messageReceived)
    else:
        socketio.emit('receivedEvent', {'data':{'message':'Listening to Platform Events...'}}, callback=messageReceived)


def logOutAndUnsubscribe( refresh=True ):
    if info.eventPath != "":
        info.client.unsubscribe(info.eventPath)
    if( refresh ):
        home()


def getAccessToke( code ):
    authURL = 'https://'+orgDomain+'/services/oauth2/token?'
    authURL += 'grant_type=authorization_code&'
    authURL += 'code='+code
    authURL += '&client_id='+cons.CLIENT_ID
    authURL += '&client_secret='+cons.CLIENT_SECRET
    authURL += '&redirect_uri='+cons.REDIRECT_URL
    req = requests.post( authURL )
    reqResult = loads(req.content)
    return reqResult


class info:
    eventPath = None
    client = None
    loop = None
    org_url = None
    refresh_token = None

##Running the app
if __name__ == '__main__':
    socketio.run(app)