import os
import json
import user_requests
import database_users

from flask import Flask
from flask import request, abort
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


localhost_url = "http://54.91.104.100:%d" %(port)

@app.before_request
def before_request():
    if request.method == 'PUT' or request.method == 'POST':
        if not request.is_json:
            raise BadRequest('Content-Type unrecognized')


@app.route("/api/v1/users", methods={'PUT'})
def add_user():
    body = request.json
    ## this step is to validate
    user_request = user_requests.CreateUserRequests(body)
    body['action'] = 'get_user'
    response = r.post("%s/api/v1/db/read" % (localhost_url), json = body)

    print (response.text)

    if response.status_code == 200:
        raise BadRequest("user %s already exists" % (user_request.getUsername()))

    body['action'] = 'add_user'

    response = r.post("%s/api/v1/db/write" % (localhost_url), json = body)

    print (response.text)

    if response.status_code != 201:
        raise BadRequest("some error occurred")

    return Response(None, status=201, mimetype='application/json')


@app.route("/api/v1/users/<username>", methods={'DELETE'})
def delete_user(username):
    body = {}
    body['action'] = 'get_user'
    body['username'] = username
    response = r.post("%s/api/v1/db/read" % (localhost_url), json = body)

    if response.status_code != 200:
        raise BadRequest('user %s not found' % (username))

    body['action'] = 'delete_user'

    response = r.post("%s/api/v1/db/write" % (localhost_url), json = body)

    if response.status_code != 201:
        raise BadRequest("some error occurred")

    return Response(None, status=200, mimetype='application/json')


@app.route("/api/v1/users", methods={'GET'})
def list_users():
    body = {
        "action": "list_users"
    }

    response = r.post("%s/api/v1/db/read" % (localhost_url), json = body)
    
    if response.status_code != 200:
        raise BadRequest("some error occurred")
    
    return Response(response.text, status=200, mimetype='application/json')

def db_add_user(json):
    if "username" not in json:
        raise BadRequest("username not passed")
    if "password" not in json:
        raise BadRequest("password not passed")

    database_users.User(username = json["username"], password = json["password"]).store()

def db_get_user(json):
    user = database_users.User.getByUsername(json["username"])
    if user is None:
        raise BadRequest("user not found")
    return {"username": user.username, "password": user.password}

def db_delete_user(json):
    if "username" not in json:
        raise BadRequest("username not passed")
    database_users.User.getByUsername(json["username"]).delete()

def db_list_users(json):
    users=database_users.User.getUsers()
    user_list=[]
    for user in users:
        user_list.append(user.username)
    return(user_list)
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
    else:
        raise BadRequest("unrecognized action %s" % (action))
    


@app.route("/")
def unsupported_path():
    return Response(json.dumps({}), status=200, mimetype='application/json')

def db_delete_db(json):
    users=database_users.User.getUsers()
    for user in users:
        database_users.User.getByUsername(user.username).delete()
    rides=database_users.Ride.getRides()
    for ride in rides:
        database_users.Ride.getByRideId(ride.ride_id).delete()
if __name__ == "__main__":
    project_dir = os.path.dirname(os.path.abspath(__file__))
    database_file = "sqlite:///{}".format(
        os.path.join(project_dir, "rideshare.db"))

    # initialize database
    engine = create_engine(database_file, echo=True)
    database_users.Base.metadata.create_all(engine, checkfirst=True)
    session_factory = sessionmaker(bind=engine)

    session = flask_scoped_session(session_factory, app)

    app.run(port=port,debug=True)
