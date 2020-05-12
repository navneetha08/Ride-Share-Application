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
import logging
from kazoo.client import KazooClient,KazooState
from threading import Timer
import docker
import sys
import database
from flask import Flask
import requests as r

logging.basicConfig()
port=8080
localhost_url='http://127.0.0.1:8080'
'''
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))

channel = connection.channel()
'''
connection = pika.BlockingConnection(pika.ConnectionParameters(host='rmq',heartbeat=0))
channel = connection.channel()
c_name = sys.argv[1]
dockerClient = docker.APIClient()
global pid
pid = int(dockerClient.inspect_container(str(c_name))['State']['Pid'])
#pid = os.environ('PID')
#c_connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq',heartbeat=300))
#c_channel = c_connection.channel()

class ZooKeeperConnect(object):
    master = False
    def __init__(self):
        self.zk = KazooClient(hosts='zoo:2181')
        self.zk.start()
        self.zk.ensure_path('/workers')
        #code to get container PID => self.PID=PID
        #self.PID=pid
        self.w_queue=''
        self.node_path = self.zk.create('/workers/node',ephemeral=True,sequence=True,value=bytes(str(pid),'utf-8')) #value='self.PID'
        '''
        try:
            master_id, master_stat = self.zk.get('/workers/master',watch=am_i_leader)
        except (NoNodeError,ZookeeperError):            
            self.zk.create_async('/workers/master',b'1000',ephemeral=True)
            self.zk.delete(self.node_path)
        '''

    def get_master_id(self):
        try:
            master_id, master_stat = self.zk.get('/election/leader')
            return master_id
        except Exception as ex:
            print(ex)
            return None

    def am_i_leader(self):
        master_id = self.get_master_id()
        if master_id is not None:
            if (master_id.decode('utf-8') == pid):
                return True
            else:
                return False
        else:
            return False
    
    def create_master_node(self):
        self.zk.create('/workers/master',bytes(str(pid),'utf-8'),ephemeral=True)
        self.zk.delete(self.node_path)
 
        
zookeepersession = ZooKeeperConnect()


read_result = channel.queue_declare(queue='read_queue',)
sync_result = channel.queue_declare(queue='sync_queue',)
write_result = channel.queue_declare(queue='write_queue',)
r_queue = read_result.method.queue
s_queue = sync_result.method.queue
w_queue = write_result.method.queue
'''
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

def db_create_ride(json):
    if "created_by" not in json:
        raise BadRequest("created_by user not passed")
    if "source" not in json:
        raise BadRequest("source not passed")
    if "destination" not in json:
        raise BadRequest("destination not passed")
    if "timestamp" not in json:
        raise BadRequest("timestamp not passed")
    print('maybe creating ride')
    #timestamp = user_requests.CreateRideRequests.validateTimestamp(json["timestamp"])
    cmd="insert into ride ('created_by','source','destination','timestamp') values("+"'"+json['created_by']+"',"+str(json['source'])+","+str(json['destination'])+","+str(json['timestamp'])+")"
   
    with engine.connect() as connection:
        with connection.begin():
            result=connection.execute(ride.insert(),{"created_by":json['created_by'],"source":json['source'],"destination":json['destination'],"timestamp":json['timestamp']})
    ride = database.Ride(created_by=json["created_by"], source=json["source"], destination = json["destination"], timestamp = json["timestamp"])
    ride.store()

    database.RideUsers(rideId=ride.rideId, username=json["created_by"]).store()
    print("inserting ride",result.rideId)
    return result.rideId

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
'''

def read_from_db(body):
    body = json.loads(body)
    if "action" not in body:
        raise BadRequest("action not passed")
    
    action = body["action"]
    
    if action == "list_upcoming_ride":
        #reponse=db_list_ride(body)
        response =  r.post('%s/api/v1/db_list_ride'%localhost_url,json=body)
        x={"res":Response(json.dumps(response), status=200, mimetype='application/json')}
        return(json.dumps(x)) 

    elif action == "get_ride":
        #response=db_get_ride(body)
        response =  r.post('%s/api/v1/db_get_ride'%localhost_url,json=body)
        x={"res":Response(json.dumps(response), status=200, mimetype='application/json')}
        return(json.dumps(x)) 
    elif action == "get_user":
        #response=db_get_user(body)
        response =  r.post('%s/api/v1/db_get_user'%localhost_url,json=body)
        x={"res": Response(json.dumps(response), status=200, mimetype='application/json')}
        return(json.dumps(x)) 
    elif action =="list_users":
        #response = db_list_users
        response =  r.post('%s/api/v1/db_list_users'%localhost_url,json=body)
        #x={"res": Response(json.dumps(response),status=200, mimetype='application/json')}
        return(response.text) 
    elif action =='num_ride':
        response - db_num_rides(body)
        response =  r.post('%s/api/v1/db_num_rides'%localhost_url,json=body)
        x=response.text
        x={"res": Response(json.dumps(response),status=200, mimetype='application/json')}
        return(json.dumps(x)) 
    else:
        raise BadRequest("unrecognized action %s" % (action))

def write_to_db(body):
    body = json.loads(body)
    print("in write_to_db",body)
    if "action" not in body:
        raise BadRequest("action not passed")

    action = body["action"]
    try:
        if action == "add_user":
            #db_add_user(body)
            r.post('%s/api/v1/db_add_user'%localhost_url,json=body)
            return str(200)
           # x={"res":Response(None, status=201, mimetype='application/json')}
            #return json.dumps(x) 

        elif action == "delete_user":
            #db_delete_user(body)
            r.post('%s/api/v1/db_delete_user'%localhost_url,json = body)
            #x={"res":Response(None, status=201, mimetype='application/json')}
            #return(json.dumps(x)) 

        elif action == "add_ride":
            #ride_id = db_create_ride(body)
            r.post('%s/api/v1/db_add_ride'%localhost_url,json = body)
            x={"res":Response(json.dumps({"rideId": ride_id}), status=201, mimetype='application/json')}
            return(json.dumps(x)) 
        
        elif action == "delete_ride":
           # db_delete_ride(body)
            r.post('%s/api/v1/db_delete_ride'%localhost_url,json = body)
            #x={"res":Response(None, status=201, mimetype='application/json')}
            #return(json.dumps(x)) 
        
        elif action == "join_ride":
            #db_join_ride(body)
            x={"res":Response(None, status=201, mimetype='application/json')}
            return(json.dumps(x)) 
        elif action == "delete_db":
            print(body)
            #db_delete_db(body)
            r.post('%s/api/v1/db_delete_db'%localhost_url,json = body)
            return str(200)
            #x={"res":{},"status":200}
            #return(json.dumps(x)) 
        else:
            raise BadRequest("unrecognized action %s" % (action))
    except BadRequest as ex:
        raise
    except Exception as ex:
        print(ex)
        raise BadRequest("invalid request")

def on_request_read_write(ch, method, props, body):

    if method.routing_key == 'read_queue':
        response = read_from_db(body)
    elif method.routing_key == 'write_queue':
        print("entering write")
        response = write_to_db(body)
        ch.basic_publish(exchange='',routing_key='sync_queue', body= body)
    

    print(response,method.routing_key)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)

def set_leader(data):
    if (data.decode('utf-8')==pid):
        zookeepersession.create_master_node()
        channel.basic_cancel(consumer_tag='slave_sync')
        channel.basic_cancel(consumer_tag='slave_read')
        write_result = channel.queue_declare(queue='write_queue',)
        sync_master = channel.queue_declare(queue='sync_queue',)
        w_queue = write_result.method.queue
        master_sync = sync_master.method.queue
#        channel.basic_consume(queue=w_queue, on_message_callback=on_request_read_write,consumer_tag='master_write')
        #master = True # it is master
        #code to close/block read_queue

@zookeepersession.zk.DataWatch('/workers/master')
def elect_leader(data,stat,event):
    if (data==None):
        try:
           # zookeepersession.zk.set('/election/master',bytes(zookeepersession.PID,'utf-8')) 
            zookeepersession.zk.set('/election/master',bytes(pid,'utf-8'))
        except Exception as ex:
            print(ex)
            pass
    elif (event.type=='DELETED' or event.type=='CHANGED' or event.state=='EXPIRED_SESSION'):
        if (pid<data.decode('utf-8')):
            zookeepersession.zk.set('/election/master',bytes(str(pid),'utf-8'))
            t = Timer(10.0,set_leader,[data])
            t.start()
#    else:
#     continue

def on_request_sync(ch, method, props, body):
    if method.routing_key == 'sync_queue':
        response = write_to_db(body)
        print(response)

channel.basic_qos(prefetch_count=1)

channel.basic_consume(queue= r_queue, on_message_callback=on_request_read_write,consumer_tag='slave_read')
channel.basic_consume(queue = s_queue,on_message_callback=on_request_sync,consumer_tag='slave_sync')
channel.basic_consume(queue=w_queue, on_message_callback=on_request_read_write,consumer_tag='master_write')

'''
project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(
os.path.join(project_dir, "rideshare.db"))

    # initialize database
engine = create_engine(database_file, echo=True)
database.Base.metadata.create_all(engine, checkfirst=True)
session_factory = sessionmaker(bind=engine)
session = flask_scoped_session(session_factory,app)'''
print(" [x] Awaiting Read Write requests")
#app.run(port=port,debug=True)
channel.start_consuming()
