from gevent import monkey
monkey.patch_all()
from gevent.pywsgi import WSGIServer
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
db_url = "http://52.86.125.105"

global num_http_users
num_http_users=0

@app.before_request
def before_request():
    if request.method == 'PUT' or request.method == 'POST':
        if not request.is_json:
            raise BadRequest('Content-Type unrecognized')


@app.route("/api/v1/users", methods={'PUT'})
def add_user():
    global num_http_users
    num_http_users+=1
    body = request.json
    ## this step is to validate
    user_request = user_requests.CreateUserRequests(body)
    body['action'] = 'get_user'
    response = r.post("%s/api/v1/db/read" % (db_url), json = body)

    print (response.text)

    if response.status_code == 200:
        raise BadRequest("user %s already exists" % (user_request.getUsername()))

    body['action'] = 'add_user'

    response = r.post("%s/api/v1/db/write" % (db_url), json = body)

    print (response.text)

    if response.status_code != 200:
        raise BadRequest("some error occurred")

    return Response(None, status=201, mimetype='application/json')


@app.route("/api/v1/users/<username>", methods={'DELETE'})
def delete_user(username):
    global num_http_users
    num_http_users+=1
    body = {}
    body['action'] = 'get_user'
    body['username'] = username
    response = r.post("%s/api/v1/db/read" % (db_url), json = body)

    if response.status_code != 200:
        raise BadRequest('user %s not found' % (username))

    body['action'] = 'delete_user'

    response = r.post("%s/api/v1/db/write" % (db_url), json = body)

    if response.status_code != 200:
        raise BadRequest("some error occurred")

    return Response(None, status=200, mimetype='application/json')


@app.route("/api/v1/users", methods={'GET'})
def list_users():
    print("in function")
    global num_http_users
    num_http_users+=1
    print("enter")
    body = {
        "action": "list_users"
    }
    response = r.post("%s/api/v1/db/read" % (db_url), json = body)
    print(response.text)
    if response.status_code != 200:
        raise BadRequest("some error occurred")

    return Response(response.text, status=200, mimetype='application/json')
@app.route("/api/v1/_count", methods={'GET'})
def count_http_user():
    l=[]
    global num_http_users
    l.append(num_http_users)
    print(l)
    return Response(json.dumps(l), status=200, mimetype='application/json')

@app.route("/api/v1/_count", methods={'DELETE'})
def reset_http_user():
    
    global num_http_users
    num_http_users=0
    return Response(json.dumps(dict()), status=200, mimetype='application/json')

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

@app.route("/")
def unsupported_path():
    return Response(json.dumps(dict()),status=200, mimetype='application/json')

if __name__ == "__main__":
    app.run(debug=True,port=port,host='0.0.0.0')
    http_user=WSGIServer(('',80),app)
    http_user.serve_forever()
