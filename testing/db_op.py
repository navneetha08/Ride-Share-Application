from flask import Flask
from flask import request, abort, jsonify, render_template
import os
import uuid
import json
from werkzeug.exceptions import BadRequest
from flask import Response
import docker
port = 8080
app = Flask(__name__)
import logging
from datetime import timedelta
import time
from math import ceil
import requests as r
import database
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy_session import flask_scoped_session


@app.route('/api/v1/db_delete_db',methods={'POST'})
def db_delete_db():
    json = request.json
    users=database.User.getUsers()

    for user in users:

        database.User.getByUsername(user.username).delete()

    rides=database.Ride.getRides()

    for ride in rides:

        database.Ride.getByRideId(ride.rideId).delete()
    return str(200)

@app.route('/api/v1/db_list_users',methods={'POST'})
def db_list_users():
    json = request.json()
    users=database.User.getUsers()

    user_list=[]

    for user in users:

        user_list.append(user.username)

    res={"res":user_list}
    return(Response(json.dumps(res),status=200,mimetype='application/json'))

@app.route('/api/v1/db_create_ride',methods={'POST'})
def db_create_ride():
    json = request.json()
    if "created_by" not in json:

        raise BadRequest("created_by user not passed")

    if "source" not in json:

        raise BadRequest("source not passed")

    if "destination" not in json:

        raise BadRequest("destination not passed")

    if "timestamp" not in json:

        raise BadRequest("timestamp not passed")



    timestamp = json["timestamp"]



    ride = database.Ride(created_by=json["created_by"], source=json["source"], destination = json["destination"], timestamp = timestamp)

    ride.store()



    database.RideUsers(ride_id=ride.ride_id, username=json["created_by"]).store()

    #return ride.ride_id
    
    #user_list.append(user.username)


    res={"res":ride.rideId}
    return(Response(json.dumps(res),status=200,mimetype='application/json'))
                                                                          

@app.route('/api/v1/db_delete_ride',methods={'POST'})
def db_delete_ride():
    json = request.json()
    if "ride_id" not in json:

        raise BadRequest("ride_id not passed")

    database.Ride.getByRideId(json["ride_id"]).delete()

    #return(Response({},status=200,mimetype='application/json'))



@app.route('/api/v1/db_join_ride',methods={'POST'})
def db_join_ride():
    json = request.json()
    if "ride_id" not in json:

        raise BadRequest("ride_id not passed")

    if "username" not in json:

        raise BadRequest("username not passed")



    #ride = database.Ride.getByRideId(json["ride_id"])

    if ride is not None:

        database.RideUsers(

            username=json["username"], ride_id=json["ride_id"]).store()

    else:

        raise BadRequest("ride_id %d not found" % json["ride_id"])
    return(Response({},status=200,mimetype='application/json'))


@app.route('/api/v1/db_get_ride',methods={'POST'})
def db_get_ride(json):
    json = request.json()
    if "ride_id" not in json:

        raise BadRequest("ride_id not passed")



    ride = database.Ride.getByRideId(json["ride_id"])

    if ride is not None:

        users = list()

        for ride_user in database.RideUsers.getByRideId(ride.ride_id):

            users.append(ride_user.username)

    response = {"ride_id": ride.ride_id, "username": users,

                "timestamp": ride.timestamp.strftime("%d-%m-%Y:%S-%M-%H"), "source": ride.source, "destination": ride.destination}

    res={"res":response}
    return(Response(json.dumps(res),status=200,mimetype='application/json'))




@app.route('/api/v1/db_num_rides',methods={'POST'})
def db_num_rides(json):
    json = request.json()
    users=database.Ride.getRides()

    l=[]

    l.append(len(users))

    res={"res":l}
    return(Response(json.dumps(res),status=200,mimetype='application/json'))    

    

@app.route('/api/v1/db_list_ride',methods={'POST'})
def db_list_ride(json):
    json = request.json()
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
    res={"res":response}

    return Response(json.dumps(res),status=200,mimetype='application/json')



@app.route('/api/v1/db_add_user',methods={'POST'})
def db_add_user(json):
    json = request.json()
    if "username" not in json:

        raise BadRequest("username not passed")

    if "password" not in json:

        raise BadRequest("password not passed")



    database.User(username = json["username"], password = json["password"]).store()
    return(str(200))
    #return(Response({},status=200,mimetype='application/json'))    


@app.route('/api/v1/db_get_user',methods={'POST'})
def db_get_user(json):

    user = database.User.getByUsername(json["username"])

    if user is None:

        raise BadRequest("user not found")

    result= {"res":{"username": user.username, "password": user.password}}
    return Response(json.dumps(result),status=200,mimetype='application/json')


@app.route('/api/v1/db_delete_user',methods={'POST'})
def db_delete_user(json):

    if "username" not in json:

        raise BadRequest("username not passed")

    database.User.getByUsername(json["username"]).delete()
    #return(Response({},status=200,mimetype='application/json'))    




if __name__ == "__main__":
     project_dir = os.path.dirname(os.path.abspath(__file__))
     database_file = "sqlite:///{}".format(os.path.join(project_dir, "rideshare.db"))
# initialize database
     engine = create_engine(database_file, echo=True)
     database.Base.metadata.create_all(engine, checkfirst=True)
     session_factory = sessionmaker(bind=engine)
     session = flask_scoped_session(session_factory, app)
     app.run(port = port,debug=True,host="0.0.0.0")
