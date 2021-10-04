import asyncio
from aiosfstream import SalesforceStreamingClient, RefreshTokenAuthenticator, Client
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))    #Generate toekn
from json import loads
import requests
from urllib.parse import urlparse
import utility.constants as cons
import nest_asyncio

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) #Generating the secret key
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config.from_object(__name__)
Session(app)
nest_asyncio.apply()

socketio = SocketIO(app, logger=True, engineio_logger=True, async_mode="threading") #Initiating SocketIo
socketio.init_app(app, cors_allowed_origins="*")

@app.route('/', methods=['POST', 'GET'])
def home():
    authUrl = 'client_id='+cons.CLIENT_ID
    authUrl += '&redirect_uri='+cons.REDIRECT_URL
    authUrl += '&response_type='+cons.RESPONSE_TYPE
    if( session.get('promptLogin') ):
        authUrl += '&prompt=login'
        session['promptLogin'] = False
    authUrlProd = cons.PROD_URL+authUrl #Oauth2.0 url for Production
    authUrlSand = cons.SANDBOX_URL+authUrl #Oauth2.0 url for Sandbox
    return render_template("index.html", token='', actionUrlProd=authUrlProd, actionUrlSand=authUrlSand) #Calling Home Page


#Method calls when the Salesforce Oauth redirects with Code.
@app.route('/oauth2/callback', methods=['POST', 'GET'])
def oauthCallback():
    # global domain
    # domain = urlparse(request.url_root).netloc
    session['authDetails'] = getAccessToke( request.args.get('code') )
    if( session.get('authDetails') != None ):
        session['refresh_token'] = session.get('authDetails').get('refresh_token')
        session['org_url'] = urlparse(session.get('authDetails').get('instance_url')).netloc
    else:
        return render_template( 'error.html' )
    
    return render_template( 'redirectingTemp.html', urlToOpen='/subscribeToPE' )


#Method stores the Org Domain
@app.route('/getOrgType', methods=['POST', 'GET'])
def getOrgType():
    if( request.form.get('OrgType') == 'sandbox' ):
        session['orgDomain'] = cons.SANDBOX_DOMAIN
    else:
        session['orgDomain'] = cons.PROD_DOMAIN
    session.modified = True
    return render_template( 'EventSubscription.html' )


#Renders the EventSubscription template.
@app.route('/subscribeToPE', methods=['POST', 'GET'])
def getPEDetails():
    return render_template("EventSubscription.html", org_name=session.get('org_url') )


#Method is called from the Socket of Javascript
@socketio.on('eventToSubscribe')
def stream_events(eventDetails, methods=['GET', 'POST']):
    try:
        session['eventName'] = eventDetails['evtname']
        session['channelType'] = eventDetails['channeltype']
        session['clientKey'] = eventDetails['clientKey']
        if( session.get('loop') is None ):
            session['loop'] = asyncio.new_event_loop()
            session['loop'].run_until_complete(perform_message( session.get('eventName'), session.get('channelType') ))
        else:
            send_fut = asyncio.run_coroutine_threadsafe( perform_message( session.get('eventName'), session.get('channelType') ), session.get('loop'))
    except Exception as e:
        socketio.emit('receivedEvent', {'data':{'error':str(e), 'message':'Sorry something went wrong!!', 'clientKey':session['clientKey']}}, callback=messageReceived)


#Method work as a Callback value
def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')


#Method perfrom Auth for the Event Subscription and Subscribes to the Event
async def perform_message( eventName, channelType ):
    listeningTo = ( 'Push Topics' if channelType == 'topic' else 'Platform Events' )
    eventPath = "/"+channelType+"/"+eventName
    isSandbox = False
    if( session.get('unSubEventsOnly') == True and session.get('client') is not None ):
        session['unSubEventsOnly'] = False
        await session.get('client').unsubscribe(session.get('eventPath'))
        session['client'] = None
        session['eventPath'] = None

    else:
        session['unSubEventsOnly'] = False
        if( session.get('client') is None ):
            auth = RefreshTokenAuthenticator(
                    consumer_key=cons.CLIENT_ID,
                    consumer_secret=cons.CLIENT_SECRET,
                    refresh_token=session.get('refresh_token'),
                    sandbox=cons.SANDBOX_DOMAIN == session.get('orgDomain')
                )
            
            client = Client(auth) #Authorizing the client with Refresh Token.

            session['client'] = client
            await session.get('client').open()
            if( session.get('eventPath') is not None and session.get('eventPath') != eventPath ):
                await session.get('client').unsubscribe(session.get('eventPath'))
        
        if( session.get('eventPath') is None or (session.get('eventPath') != eventPath) ):
            
            if( session.get('eventPath') is not None and session.get('eventPath') != eventPath ):
                await session.get('client').unsubscribe(session.get('eventPath'))

            session['eventPath'] = eventPath
            await session.get('client').subscribe(eventPath) #Subscribing to Event

            socketio.emit('receivedEvent', {'data':{'message':'Listening to '+listeningTo+'...', 'clientKey':session['clientKey']}}, callback=messageReceived)
            
            # listen for incoming messages
            async for message in session.get('client'):
                data = message["data"]
                payload = None
                
                if 'payload' in data:
                    payload = data["payload"]
                else:
                    payload = data['sobject']
                socketio.emit('receivedEvent', {'data':{'payload':payload, 'clientKey':session['clientKey']}}, callback=messageReceived)
                 #Once the PE published from SF send it to JS
        else:
            socketio.emit('receivedEvent', {'data':{'message':'Listening to '+listeningTo+'...', 'clientKey':session['clientKey']}}, callback=messageReceived)


#Method logs out user
@app.route('/logout', methods=['POST', 'GET'])
def logOutAndUnsubscribe():
    session['unSubEventsOnly'] = True
    session['promptLogin'] = True
    if( session.get('loop') is not None ):
        send_fut = asyncio.run_coroutine_threadsafe( perform_message( session.get('eventName'), session.get('channelType') ), session.get('loop'))
    session['unSubEventsOnly'] = False
    return render_template( 'redirectingTemp.html', urlToOpen='/' )


async def unsubscribe():
    if( session.get('client') is not None ):
        await session.get('client').unsubscribe(session.get('eventPath'))

#Method gets the Access Token with the value of Code returned by OAuth
def getAccessToke( code ):
    authURL = 'https://'+session.get('orgDomain')+'/services/oauth2/token?'
    authURL += 'grant_type=authorization_code&'
    authURL += 'code='+code
    authURL += '&client_id='+cons.CLIENT_ID
    authURL += '&client_secret='+cons.CLIENT_SECRET
    authURL += '&redirect_uri='+cons.REDIRECT_URL
    req = requests.post( authURL )
    reqResult = loads(req.content)
    return reqResult

##Running the app
if __name__ == '__main__':
    socketio.run(app)