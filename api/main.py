import asyncio
from aiosfstream import SalesforceStreamingClient, RefreshTokenAuthenticator, Client
from flask_socketio import SocketIO, emit
from flask.json import jsonify
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))    #Generate toekn
from json import loads, dumps
import requests
from urllib.parse import urlparse
import utility.constants as cons
import nest_asyncio
import grpc
import requests
import threading
import io
import pubsub_api_pb2 as pb2
import pubsub_api_pb2_grpc as pb2_grpc
import avro.schema
import avro.io
import time
import certifi


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) #Generating the secret key
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config.update(SESSION_COOKIE_SAMESITE="None", SESSION_COOKIE_SECURE=True)
app.config.from_object(__name__)
Session(app)
nest_asyncio.apply()
cache = {}
semaphore = threading.Semaphore(1)
latest_replay_id = None

# socketio = SocketIO(app, logger=True, engineio_logger=True, async_mode="threading") #Initiating SocketIo
# socketio.init_app(app, cors_allowed_origins="*")

## Method does fetch request for platform event
def fetchReqStream(topic):
    while True:
        semaphore.acquire()
        yield pb2.FetchRequest(
            topic_name = topic,
            replay_preset = pb2.ReplayPreset.LATEST,
            num_requested = 1)

## Method decodes the incoming Event response
def decode(schema, payload):
    schema = avro.schema.parse(schema)
    buf = io.BytesIO(payload)
    decoder = avro.io.BinaryDecoder(buf)
    reader = avro.io.DatumReader(schema)
    ret = reader.read(decoder)
    return ret

## Method gets called for authentication
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
    session['authDetails'] = getAccessToke( request.args.get('code') )
    if( session.get('authDetails') != None ):
        print('access_token', session.get('authDetails').get('access_token') )
        print('all info', session.get('authDetails') )
        session['access_token'] = session.get('authDetails').get('access_token')
        getOrgId()
        session['refresh_token'] = session.get('authDetails').get('refresh_token')
        session['org_url'] = urlparse(session.get('authDetails').get('instance_url')).netloc
        session['instance_url'] = session.get('authDetails').get('instance_url')
        print('org url--',session['instance_url'])
    else:
        return render_template( 'error.html' )
    
    return render_template( 'redirectingTemp.html', urlToOpen='/subscribeToPE' )

## Method decodes Org ID from URL
def getOrgId():
    orgUrl = session.get('authDetails').get('id')
    orgId = orgUrl[ orgUrl.index( '/id/' )+4: len(orgUrl) ]
    orgId = orgId[ 0 : orgId.index('/') ]
    print('ordId--'+orgId)
    session['org_id'] = orgId

#Method stores the Org Domain
@app.route('/getOrgType', methods=['POST', 'GET'])
def getOrgType():
    if( request.form.get('OrgType') == 'sandbox' ):
        session['orgDomain'] = cons.SANDBOX_DOMAIN
    else:
        session['orgDomain'] = cons.PROD_DOMAIN
    session.modified = True
    return render_template( 'EventSubscription.html' )

## Method maintains ClientKey
@app.route('/getReceivedDetails', methods=['POST', 'GET'])
def getReceivedDetails():
    clientKey = request.args.get('clientKey')
    if( clientKey ):
        return dumps(cache[clientKey])


## Renders the EventSubscription template.
@app.route('/subscribeToPE', methods=['POST', 'GET'])
def getPEDetails():
    return render_template("EventSubscription.html", org_name=session.get('org_url') )

## Method gets called on Subscribe button and Subscribe the Event
@app.route('/eventDetails', methods=['POST'])
def handleEventDetails():
    return stream_events3( request.json['eventName'], request.json['eventType'], request.json['clientKey'] )

def stream_events3( eventName, eventType, clientKey ):
    try:
        session['eventName'] = eventName
        session['channelType'] = eventType
        session['clientKey'] = clientKey
        print('here1-->',session['eventName'], session['channelType'])
        if( session.get('loop') is None ):
            cache[clientKey] = []
       
        handleEvents()
        return dumps({'success':True, 'clientKey':session['clientKey']}), 200, {'ContentType':'application/json'} 
    except Exception as e:
        print('here4-->',e)
        return dumps({'success':False, 'clientKey':session['clientKey'], 'message': 'Sorry something went wrong!!'}), 400, {'ContentType':'application/json'} 

#portNum = 7443
def handleEvents():

    clientKey = session['clientKey']
    exStub = session.get('stub')
    print('exStub--',exStub)
    with open(certifi.where(), 'rb') as f:
        creds = grpc.ssl_channel_credentials(f.read())
    
    portNum = '7443'
    with grpc.secure_channel('api.pubsub.salesforce.com:'+portNum, creds) as channel:

        # if( session.get('unSubEventsOnly') == True and session.get('client') is not None ):
        #     session['unSubEventsOnly'] = False
        #     await session.get('client').unsubscribe(session.get('eventPath'))
        #     session['client'] = None
        #     session['eventPath'] = None

        sessionid = session.get('access_token')
        instanceurl = session.get('instance_url')
        tenantid = session.get('org_id');
        authmetadata = (('accesstoken', sessionid),
        ('instanceurl', instanceurl),
        ('tenantid', tenantid))

        if( exStub is None ):
            stub = pb2_grpc.PubSubStub(channel)
            session['stub'] = stub
        else:
            stub = exStub

        mysubtopic = "/"+session.get('channelType')+"/"+session.get('eventName')
        #mysubtopic = "/event/Notification__e"
        print('Subscribing to ' + mysubtopic)
        substream = stub.Subscribe(fetchReqStream(mysubtopic),
                metadata=authmetadata)
        for event in substream:
            if( event is not None ):
                if event.events:
                    semaphore.release()
                print("Number of events received: ", len(event.events))
                if( len(event.events) > 0 ):
                    payloadbytes = event.events[0].event.payload
                    schemaid = event.events[0].event.schema_id
                    schema = stub.GetSchema(
                            pb2.SchemaRequest(schema_id=schemaid),
                            metadata=authmetadata).schema_json
                    decoded = decode(schema, payloadbytes)
                    cache[clientKey].append(decoded) 
                    print("Got an event!", decoded)
            else:
                print("[", time.strftime('%b %d, %Y %l:%M%p %Z'),
                "] The subscription is active.")
            latest_replay_id = event.latest_replay_id


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
    app.run(debug=True)
    socketio.run(app)