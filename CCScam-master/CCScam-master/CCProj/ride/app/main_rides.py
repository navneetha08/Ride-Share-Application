from gevent import monkey
monkey.patch_all()
from gevent.pywsgi import WSGIServer
import os
import json
import ride_requests
import database_rides
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

port = 8000
app = Flask(__name__)


localhost_url = "http://127.0.0.1:%d" %(port)

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
    url="http://users"
    response = r.get("%s/api/v1/users" % (url),json=body)
    print(response.text)
  
    if(body['username'] not in response.text):
        raise BadRequest('user %s not found' % (body['username']))

    body=request.json
    body['action'] = 'add_ride'
    ride_request = ride_requests.CreateRideRequests(body)

    response = r.post("%s/api/v1/db/write" % (localhost_url), json = body)

    if response.status_code != 201:
        print (response.text)
        raise BadRequest("some error occurred")

    return Response(response.text, status=201, mimetype='application/json')


@app.route("/api/v1/rides", methods={'GET'})
def list_upcoming_ride():
    global num_http_rides
    num_http_rides+=1
    source = ""
    destination = ""
    try:
        source = user_requests.CreateRideRequests.validateSource(
            request.args.get("source"))
        destination = user_requests.CreateRideRequests.validateDestination(
            request.args.get("destination"))
    except Exception as ex:
        raise BadRequest("request arguments source, destination are mandatory")

    body = {
        "action": "list_upcoming_ride",
        "source": source,
        "destination": destination
    }

    response = r.post("%s/api/v1/db/read" % (localhost_url), json = body)
    if response.status_code != 200:
        raise BadRequest("some error occurred")
    
    return Response(response.text, status=200, mimetype='application/json')


@app.route("/api/v1/rides/<int:ride_id>", methods={'GET'})
def get_ride(ride_id):
    global num_http_rides
    num_http_rides+=1
    body = {
        "action": "get_ride",
        "ride_id": ride_id
    }

    response = r.post("%s/api/v1/db/read" % (localhost_url), json = body)

    if response.status_code != 200:
        raise BadRequest("some error occurred")
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
@app.route("/api/v1/rides/<int:ride_id>", methods={'POST'})
def join_ride(ride_id):
    global num_http_rides
    num_http_rides+=1
    if 'username' not in request.json:
        raise BadRequest("username is mandatory in request")

    body = {}
    body['username'] = request.json['username']
    url="http://users"
    response = r.get("%s/api/v1/users" % (url),json=body)
    print(response.text)
  
    if(body['username'] not in response.text):
        raise BadRequest('user %s not found' % (body['username']))
    
    
    body = request.json
    body["action"] = "join_ride"
    body["ride_id"] = ride_id
    response = r.post("%s/api/v1/db/write" % (localhost_url), json = body)

    if response.status_code != 201:
        raise BadRequest("some error occurred")

    return Response(None, status=200, mimetype='application/json')


@app.route("/api/v1/rides/<int:ride_id>", methods={'DELETE'})
def delete_ride(ride_id):
    global num_http_rides
    num_http_rides+=1
    body = {}
    body["action"] = "delete_ride"
    body["ride_id"] = ride_id
    response = r.post("%s/api/v1/db/write" % (localhost_url), json = body)

    if response.status_code != 201:
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

@app.route("/api/v1/db/clear", methods={'POST'})
def delete_db():
    body = {}
    body["action"] = "delete_db"
    response = r.post("%s/api/v1/db/write" % (localhost_url), json = body)
    if response.status_code != 201:
        raise BadRequest("some error occurred")
    
    return Response(json.dumps(dict()), status=200, mimetype='application/json')

def db_create_ride(json):
    if "created_by" not in json:
        raise BadRequest("created_by user not passed")
    if "source" not in json:
        raise BadRequest("source not passed")
    if "destination" not in json:
        raise BadRequest("destination not passed")
    if "timestamp" not in json:
        raise BadRequest("timestamp not passed")

    timestamp = ride_requests.CreateRideRequests.validateTimestamp(json["timestamp"])
    
    ride = database_rides.Ride(created_by=json["created_by"], source=json["source"], destination = json["destination"], timestamp = timestamp)
    ride.store()

    database_rides.RideUsers(ride_id=ride.ride_id, username=json["created_by"]).store()
    return ride.ride_id

def db_delete_ride(json):
    if "ride_id" not in json:
        raise BadRequest("ride_id not passed")
    database_rides.Ride.getByRideId(json["ride_id"]).delete()

def db_join_ride(json):
    if "ride_id" not in json:
        raise BadRequest("ride_id not passed")
    if "username" not in json:
        raise BadRequest("username not passed")

    ride = database_rides.Ride.getByRideId(json["ride_id"])
    if ride is not None:
        database_rides.RideUsers(
            username=json["username"], ride_id=json["ride_id"]).store()
    else:
        raise BadRequest("ride_id %d not found" % json["ride_id"])

def db_get_ride(json):
    if "ride_id" not in json:
        raise BadRequest("ride_id not passed")

    ride = database_rides.Ride.getByRideId(json["ride_id"])
    if ride is not None:
        users = list()
        for ride_user in database_rides.RideUsers.getByRideId(ride.ride_id):
            users.append(ride_user.username)
    response = {"ride_id": ride.ride_id, "username": users,
                "timestamp": ride.timestamp.strftime("%d-%m-%Y:%S-%M-%H"), "source": ride.source, "destination": ride.destination}
    return response

def db_list_ride(json):
    if "source" not in json:
        raise BadRequest("source not passed")
    if "destination" not in json:
        raise BadRequest("destination not passed")
    
    rides = database_rides.Ride.listUpcomingRides(json["source"], json["destination"])
    response = list()
    if rides is not None and len(rides) > 0:
        for ride in rides:
            users = list()
            for ride_user in database_rides.RideUsers.getByRideId(ride.ride_id):
                users.append(ride_user.username)
            response.append({"ride_id": ride.ride_id, "username": users,
                                "timestamp": ride.timestamp.strftime("%d-%m-%Y:%S-%M-%H")})
    return response

def db_delete_db(json):
    users=database_users.User.getUsers()
    for user in users:
        database_users.User.getByUsername(user.username).delete()
    rides=database_rides.Ride.getRides()
    for ride in rides:
        database_rides.Ride.getByRideId(ride.ride_id).delete()
def db_num_rides(json):
    users=database_rides.Ride.getRides()
    l=[]
    l.append(len(users))
    return(l)


@app.route("/api/v1/db/write", methods={'POST'})
def write_to_db():
    body = request.get_json()
    if "action" not in body:
        raise BadRequest("action not passed")

    action = body["action"]
    try:
        if action == "add_user":
            db_add_user(body)
            return Response(None, status=201, mimetype='application/json')

        elif action == "delete_user":
            db_delete_user(body)
            return Response(None, status=201, mimetype='application/json')

        elif action == "add_ride":
            print("here")
            ride_id = db_create_ride(body)
            return Response(json.dumps({"ride_id": ride_id}), status=201, mimetype='application/json')
        
        elif action == "delete_ride":
            db_delete_ride(body)
            return Response(None, status=201, mimetype='application/json')
        
        elif action == "join_ride":
            db_join_ride(body)
            return Response(None, status=201, mimetype='application/json')

        elif action == "delete_db":
            db_delete_db(body)
            return Response(None, status=201, mimetype='application/json')
        else:
            raise BadRequest("unrecognized action %s" % (action))
    except BadRequest as ex:
        raise
    except Exception as ex:
        print(ex)
        raise BadRequest("invalid request")



@app.route("/api/v1/db/read", methods={'POST'})
def read_from_db():
    body = request.get_json()
    if "action" not in body:
        raise BadRequest("action not passed")
    
    action = body["action"]
    
    if action == "list_upcoming_ride":
        return Response(json.dumps(db_list_ride(body)), status=200, mimetype='application/json')
    elif action == "get_ride":
        return Response(json.dumps(db_get_ride(body)), status=200, mimetype='application/json')
    elif action == "get_user":
        return Response(json.dumps(db_get_user(body)), status=200, mimetype='application/json')
    elif action =="list_users":
        return Response(json.dumps(db_list_users(body)),status=200, mimetype='application/json')
    elif action =='num_ride':
        return Response(json.dumps(db_num_rides(body)),status=200, mimetype='application/json')
    else:
        raise BadRequest("unrecognized action %s" % (action))
    


@app.route("/")
def unsupported_path():
    raise MethodNotAllowed()


if __name__ == "__main__":
    project_dir = os.path.dirname(os.path.abspath(__file__))
    database_file = "sqlite:///{}".format(
        os.path.join(project_dir, "rideshare.db"))

    # initialize database
    engine = create_engine(database_file, echo=True)
    database_rides.Base.metadata.create_all(engine, checkfirst=True)
    session_factory = sessionmaker(bind=engine)

    session = flask_scoped_session(session_factory, app)

#    app.run(port=port,debug=True)
     http_ride=WSGIServer(('',80),app)
     http_ride.serve_forever()