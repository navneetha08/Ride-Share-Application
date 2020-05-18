from gevent import monkey
monkey.patch_all()
from gevent.pywsgi import WSGIServer
import os
import json
import ride_requests
#import database_rides
from flask import Flask
from flask import request, abort, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy_session import flask_scoped_session
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import NotFound
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import MethodNotAllowed
import traceback
import requests as r

port = 80
app = Flask(__name__)


localhost_url = "http://52.86.125.105"

global num_http_rides
num_http_rides=0

@app.before_request
def before_request():
    if request.method == 'PUT' or request.method == 'POST':
        if not request.is_json:
            raise BadRequest('Content-Type unrecognized')


@app.route("/api/v1/rides", methods={'POST'})
def add_ride():
    global num_http_rides
    num_http_rides+=1
    body = {}
    body['username'] = request.json['created_by']
    url="http://52.86.125.105"
    response = r.get("%s/api/v1/users" % (url),json=body)
    print(response.text)
  
    if(body['username'] not in response.text):
        raise BadRequest('user %s not found' % (body['username']))

    body=request.json
    body['action'] = 'add_ride'
    ride_request = ride_requests.CreateRideRequests(body)

    response = r.post("%s/api/v1/db/write" % (localhost_url), json = body)

    if response.status_code != 200:
        print (response.text)
        raise BadRequest("some error occurred")

    return Response(response.text, status=201, mimetype='application/json')


def validateSource(source):
        if int(source) < 1 or int(source) > 198:
            raise BadRequest("invalid source passed")
        return source

def validateDestination(destination):
    if int(destination) < 1 or int(destination) > 198:
        raise BadRequest("invalid destination passed")
    return destination

@app.route("/api/v1/rides", methods={'GET'})
def list_upcoming_ride():
    global num_http_rides
    num_http_rides+=1
    source = ""
    destination = ""
    try:
        source = validateSource(
            request.args.get("source"))
        destination = validateDestination(
            request.args.get("destination"))
    except Exception as ex:
        traceback.print_exc()
        raise BadRequest("request arguments source, destination are mandatory")

    body = {
        "action": "list_upcoming_ride",
        "source": source,
        "destination": destination
    }

    response = r.post("%s/api/v1/db/read" % (localhost_url), json = body)
    if response.status_code != 200:
        raise BadRequest("some error occurred")
    j = json.loads(response.text)
    if (len(j) == 0):
        return Response(None, status=204, mimetype='application/json')
    return Response(response.text, status=200, mimetype='application/json')


@app.route("/api/v1/rides/<int:rideId>", methods={'GET'})
def get_ride(rideId):
    global num_http_rides
    num_http_rides+=1
    body = {
        "action": "get_ride",
        "ride_id": rideId
    }

    response = r.post("%s/api/v1/db/read" % (localhost_url), json = body)

    if response.status_code != 200:
        return Response(None, status=204, mimetype='application/json')
    return Response(response.text, status=200, mimetype='application/json')

@app.route("/api/v1/rides/count", methods={'GET'})
def num_ride():
    global num_http_rides
    num_http_rides+=1
    body = {
        "action": "num_ride"
    }

    response = r.post("%s/api/v1/db/read" % (localhost_url), json = body)

    if response.status_code != 200:
        raise BadRequest("some error occurred")

    return Response(response.text, status=200, mimetype='application/json')
@app.route("/api/v1/rides/<int:rideId>", methods={'POST'})
def join_ride(rideId):
    global num_http_rides
    num_http_rides+=1
    if 'username' not in request.json:
        raise BadRequest("username is mandatory in request")

    body = {}
    body['username'] = request.json['username']
    url="http://52.86.125.105"
    response = r.get("%s/api/v1/users" % (url),json=body)
    print(response.text)
  
    if(body['username'] not in response.text):
        raise BadRequest('user %s not found' % (body['username']))
    
    
    body = request.json
    body["action"] = "join_ride"
    body["ride_id"] = rideId
    response = r.post("%s/api/v1/db/write" % (localhost_url), json = body)

    if response.status_code != 200:
        raise BadRequest("some error occurred")

    return Response(None, status=200, mimetype='application/json')


@app.route("/api/v1/rides/<int:rideId>", methods={'DELETE'})
def delete_ride(rideId):
    global num_http_rides
    num_http_rides+=1
    body = {}
    body["action"] = "delete_ride"
    body["ride_id"] = rideId
    response = r.post("%s/api/v1/db/write" % (localhost_url), json = body)

    if response.status_code != 200:
        raise BadRequest("some error occurred")
    
    return Response(None, status=200, mimetype='application/json')


@app.route("/api/v1/_count", methods={'GET'})
def count_http_ride():
    l=[]
    global num_http_rides
    l.append(num_http_rides)
    print(l)
    return Response(json.dumps(l), status=200, mimetype='application/json')


@app.route("/api/v1/_count", methods={'DELETE'})
def reset_http_ride():
    
    global num_http_rides
    num_http_rides=0
    return Response(json.dumps(dict()), status=200, mimetype='application/json')



@app.route("/")
def unsupported_path():
    return Response(json.dumps(dict()), status=200, mimetype='application/json')


if __name__ == "__main__":
    app.run(host='0.0.0.0',port=port,debug=True)
http_ride=WSGIServer(('0.0.0.0',80),app)
http_ride.serve_forever()
