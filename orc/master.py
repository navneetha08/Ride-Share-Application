import pika
import os
import json
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
import database

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))

channel = connection.channel()

result2 = channel.queue_declare(queue='write_queue',)
result1 = channel.queue_declare(queue='read_queue',)
queue_name = result1.method.queue
queue_name1 = result2.method.queue

def write_to_db(body):
    body = json.loads(body)
    if "action" not in body:
        raise BadRequest("action not passed")

    action = body["action"]
    try:
        if action == "add_user":
            db_add_user(body)
            x={"res":Response(None, status=201, mimetype='application/json')}
            return(json.dumps(x)) 

        elif action == "delete_user":
            db_delete_user(body)
            x={"res":Response(None, status=201, mimetype='application/json')}
            return(json.dumps(x)) 

        elif action == "add_ride":
            ride_id = db_create_ride(body)
            x={"res":Response(json.dumps({"ride_id": ride_id}), status=201, mimetype='application/json')}
            return(json.dumps(x)) 
        
        elif action == "delete_ride":
            db_delete_ride(body)
            x={"res":Response(None, status=201, mimetype='application/json')}
            return(json.dumps(x)) 
        
        elif action == "join_ride":
            db_join_ride(body)
            x={"res":Response(None, status=201, mimetype='application/json')}
            return(json.dumps(x)) 
        elif action == "delete_db":
            db_delete_db(body)
            x={"res":Response(None, status=201, mimetype='application/json')}
            return(json.dumps(x)) 
        else:
            raise BadRequest("unrecognized action %s" % (action))
    except BadRequest as ex:
        raise
    except Exception as ex:
        print(ex)
        raise BadRequest("invalid request")




def db_delete_db(json):
    users=database.User.getUsers()
    for user in users:
        database.User.getByUsername(user.username).delete()
    rides=database.Ride.getRides()
    for ride in rides:
        database.Ride.getByRideId(ride.rideId).delete()

def db_list_users(json):
    users=database.User.getUsers()
    user_list=[]
    for user in users:
        user_list.append(user.username)
    return(user_list)

def read_from_db(body):
    body = json.loads(body)
    if "action" not in body:
        raise BadRequest("action not passed")
    
    action = body["action"]
    
    if action == "list_upcoming_ride":
        x={"res":Response(json.dumps(db_list_ride(body)), status=200, mimetype='application/json')}
        return(json.dumps(x)) 

    elif action == "get_ride":
        x={"res":Response(json.dumps(db_get_ride(body)), status=200, mimetype='application/json')}
        return(json.dumps(x)) 
    elif action == "get_user":
        x={"res": Response(json.dumps(db_get_user(body)), status=200, mimetype='application/json')}
        return(json.dumps(x)) 
    elif action =="list_users":
        x={"res": Response(json.dumps(db_list_users(body)),status=200, mimetype='application/json')}
        return(json.dumps(x)) 
    elif action =='num_ride':
        x={"res": Response(json.dumps(db_num_rides(body)),status=200, mimetype='application/json')}
        return(json.dumps(x)) 
    else:
        raise BadRequest("unrecognized action %s" % (action))
    


def db_create_ride(json):
    if "created_by" not in json:
        raise BadRequest("created_by user not passed")
    if "source" not in json:
        raise BadRequest("source not passed")
    if "destination" not in json:
        raise BadRequest("destination not passed")
    if "timestamp" not in json:
        raise BadRequest("timestamp not passed")

    timestamp = user_requests.CreateRideRequests.validateTimestamp(json["timestamp"])

    ride = database.Ride(created_by=json["created_by"], source=json["source"], destination = json["destination"], timestamp = timestamp)
    ride.store()

    database.RideUsers(ride_id=ride.ride_id, username=json["created_by"]).store()
    return ride.ride_id

def db_delete_ride(json):
    if "ride_id" not in json:
        raise BadRequest("ride_id not passed")
    database.Ride.getByRideId(json["ride_id"]).delete()

def db_join_ride(json):
    if "ride_id" not in json:
        raise BadRequest("ride_id not passed")
    if "username" not in json:
        raise BadRequest("username not passed")

    ride = database.Ride.getByRideId(json["ride_id"])
    if ride is not None:
        database.RideUsers(
            username=json["username"], ride_id=json["ride_id"]).store()
    else:
        raise BadRequest("ride_id %d not found" % json["ride_id"])

def db_get_ride(json):
    if "ride_id" not in json:
        raise BadRequest("ride_id not passed")

    ride = database.Ride.getByRideId(json["ride_id"])
    if ride is not None:
        users = list()
        for ride_user in database.RideUsers.getByRideId(ride.ride_id):
            users.append(ride_user.username)
    response = {"ride_id": ride.ride_id, "username": users,
                "timestamp": ride.timestamp.strftime("%d-%m-%Y:%S-%M-%H"), "source": ride.source, "destination": ride.destination}
    return response


def db_num_rides(json):
    users=database.Ride.getRides()
    l=[]
    l.append(len(users))
    return(l)
    
def db_list_ride(json):
    if "source" not in json:
        raise BadRequest("source not passed")
    if "destination" not in json:
        raise BadRequest("destination not passed")
    
    rides = database.Ride.listUpcomingRides(json["source"], json["destination"])
    response = list()
    if rides is not None and len(rides) > 0:
        for ride in rides:
            users = list()
            for ride_user in database.RideUsers.getByRideId(ride.ride_id):
                users.append(ride_user.username)
            response.append({"ride_id": ride.ride_id, "username": users,
                                "timestamp": ride.timestamp.strftime("%d-%m-%Y:%S-%M-%H")})
    return response

def db_add_user(json):
    if "username" not in json:
        raise BadRequest("username not passed")
    if "password" not in json:
        raise BadRequest("password not passed")

    database.User(username = json["username"], password = json["password"]).store()

def db_get_user(json):
    user = database.User.getByUsername(json["username"])
    if user is None:
        raise BadRequest("user not found")
    return {"username": user.username, "password": user.password}

def db_delete_user(json):
    if "username" not in json:
        raise BadRequest("username not passed")
    database.User.getByUsername(json["username"]).delete()






def on_request(ch, method, props, body):

    if method.routing_key == 'read_queue':
        response = read_from_db(body)
    elif method.routing_key == 'write_queue':
        response = write_to_db(body)
    

    print(response,method.routing_key)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue= queue_name1, on_message_callback=on_request)
channel.basic_consume(queue= queue_name, on_message_callback=on_request)




project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(
os.path.join(project_dir, "rideshare.db"))

    # initialize database
engine = create_engine(database_file, echo=True)
database.Base.metadata.create_all(engine, checkfirst=True)
session_factory = sessionmaker(bind=engine)
print(" [x] Awaiting Read Write requests")
channel.start_consuming()