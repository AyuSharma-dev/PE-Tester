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
socketio = SocketIO(app, logger=True, engineio_logger=True, async_mode="threading") #Initiating SocketIo
socketio.init_app(app, cors_allowed_origins="*")

@app.route('/', methods=['POST', 'GET'])
def home():
    authUrl = 'client_id='+cons.CLIENT_ID
    authUrl += '&redirect_uri='+cons.REDIRECT_URL
    authUrl += '&response_type='+cons.RESPONSE_TYPE
    if( info.promptLogin ):
        authUrl += '&prompt=login'
        info.promptLogin = False
    authUrlProd = cons.PROD_URL+authUrl #Oauth2.0 url for Production
    authUrlSand = cons.SANDBOX_URL+authUrl #Oauth2.0 url for Sandbox
    print(authUrl)
    return render_template("index.html", token='', actionUrlProd=authUrlProd, actionUrlSand=authUrlSand) #Calling Home Page


#Method calls when the Salesforce Oauth redirects with Code.
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
    
    return render_template( 'redirectingTemp.html', urlToOpen='/subscribeToPE' )


#Method stores the Org Domain
@app.route('/getOrgType', methods=['POST', 'GET'])
def getOrgType():
    global orgDomain
    if( request.form.get('OrgType') == 'sandbox' ):
        orgDomain = cons.SANDBOX_DOMAIN
    else:
        orgDomain = cons.PROD_DOMAIN
    return render_template( 'EventSubscription.html' )


#Renders the EventSubscription template.
@app.route('/subscribeToPE', methods=['POST', 'GET'])
def getPEDetails():
    return render_template("EventSubscription.html", org_name=info.org_url )


#Method is called from the Socket of Javascript
@socketio.on('eventToSubscribe')
def stream_events(eventDetails, methods=['GET', 'POST']):
    print( eventDetails )
    try:
        info.eventName = eventDetails['evtname']
        info.channelType = eventDetails['channeltype'];
        print( 'eventName-->'+info.eventName+'---'+info.channelType )
        if( info.loop is None ):
            info.loop = asyncio.new_event_loop()
            info.loop.run_until_complete(perform_message( info.eventName, info.channelType ))
        else:
            print('inside coroutine')
            send_fut = asyncio.run_coroutine_threadsafe( perform_message( info.eventName, info.channelType ), info.loop)
    except Exception as e:
        socketio.emit('receivedEvent', {'data':{'error':str(e), 'message':'Sorry something went wrong!!'}}, callback=messageReceived)


#Method work as a Callback value
def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')


#Method perfrom Auth for the Event Subscription and Subscribes to the Event
async def perform_message( eventName, channelType ):
    global eventPath
    eventPath = "/"+channelType+"/"+eventName
    isSandbox = False
    print('At begining')
    if( info.unSubEventsOnly ):
        info.unSubEventsOnly = False
        await info.client.unsubscribe(info.eventPath)
        info.client = None
        info.eventPath = None
        print('unsubscribed')

    else:
        print('In correct else')
        if( info.client is None ):
            print('Getting Client')
            if( cons.SANDBOX_DOMAIN == orgDomain ):
                isSandbox = True

            auth = RefreshTokenAuthenticator(
                    consumer_key=cons.CLIENT_ID,
                    consumer_secret=cons.CLIENT_SECRET,
                    refresh_token=info.refresh_token,
                    sandbox=isSandbox
                )

            client = Client(auth) #Authorizing the client with Refresh Token.
            info.client = client
            print('OPening client')
            await info.client.open()
            print('Client Opened')
            if( info.eventPath is not None and info.eventPath != eventPath ):
                await info.client.unsubscribe(info.eventPath)
        
        if( info.eventPath is None or (info.eventPath != eventPath) ):
            
            if( info.eventPath is not None and info.eventPath != eventPath ):
                await info.client.unsubscribe(info.eventPath)

            info.eventPath = eventPath
            print( info.eventPath )
            await info.client.subscribe(eventPath) #Subscribing to Event

            socketio.emit('receivedEvent', {'data':{'message':'Listening to Platform Events...'}}, callback=messageReceived)
            
            # listen for incoming messages
            async for message in info.client:
                print('looking for messages')
                data = message["data"]
                print(channelType)
                print(data)
                payload = None
                
                if 'payload' in data:
                    payload = data["payload"]
                else:
                    payload = data['sobject']
                socketio.emit('receivedEvent', {'data':payload}, callback=messageReceived)
                 #Once the PE published from SF send it to JS
        else:
            print('inside else')
            socketio.emit('receivedEvent', {'data':{'message':'Listening to Streaming channel'}}, callback=messageReceived)


#Method logs out user
@app.route('/logout', methods=['POST', 'GET'])
def logOutAndUnsubscribe():
    info.unSubEventsOnly = True
    info.promptLogin = True
    send_fut = asyncio.run_coroutine_threadsafe( perform_message( info.eventName ), info.loop)
    #stream_events( {'evtname': info.eventName} )
        # asyncio.set_event_loop(loop)
        # send_fut2 = asyncio.get_event_loop()
        # send_fut2.run_until_complete( unsubscribe() )
    #     send_fut.result()
    return render_template( 'redirectingTemp.html', urlToOpen='/' )


async def unsubscribe():
    if( info.client is not None ):
        await info.client.unsubscribe(info.eventPath)

#Method gets the Access Token with the value of Code returned by OAuth
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


#Class stores basic information
class info:
    eventPath = None
    channelType = None
    client = None
    loop = None
    org_url = None
    refresh_token = None
    promptLogin = False
    eventName = None
    unSubEventsOnly = False

##Running the app
if __name__ == '__main__':
    socketio.run(app)