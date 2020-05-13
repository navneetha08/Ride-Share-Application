import pika
import os
import json
import random
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import NotFound
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import MethodNotAllowed
import database
import logging
from kazoo.client import KazooClient,KazooState
from threading import Timer
import os
import docker
import time

logging.basicConfig()

connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
channel = connection.channel()
pid = str(os.getpid())
client = docker.from_env()
slave_ctr = 0

class ZooKeeperConnect:
    def __init__(self):
        self.zk = KazooClient(hosts='zoo:2181')
        self.zk.start()
        self.zk.ensure_path('/workers')
        self.PID=str(pid)
        self.node_path = self.zk.create('/workers/node/c_',ephemeral=True, sequence=True,value=bytes(self.PID, 'utf-8'), makepath=True) #value='self.PID'
        self.master_id = None
        print ("node path is %s" % (self.node_path))
        try:
            self.create_master_node()
        except Exception as ex:
            print (ex)
            self.zk.delete(self.node_path)

    def create_master_node(self):
        if (self.zk.exists('/workers/master') == None):
            self.master_id = str(pid)
            master_node_path = self.zk.create('/workers/master/m_', bytes(self.PID, 'utf-8'), ephemeral=True, makepath=True, sequence=True)
            print ("master node path is ", master_node_path)
            self.zk.delete(self.node_path)
        else:
            self.master_id = self.zk.get(self.zk.get_children('/workers/master')[0])[0].decode('utf-8')
            print ("master node pid is ", self.master_id)

    def is_master(self):
        if self.master_id is None:
            return False
        if (self.master_id == self.PID):
            return True
        else:
            return False

zookeepersession = ZooKeeperConnect()


def create_slave_node():
    if (zookeepersession.is_master()):
        print ("creating new slave node")
        zookeepersession.zk.create('/workers/node/c_',ephemeral=True, sequence=True,value=bytes(work_cont.top(), 'utf-8'), makepath=True)
        worker_cont=client.containers.run(image="slave:latest", command='sh -c "./wait-for-it.sh -t 10 127.0.0.1:5672 -- python master_v4.py"',links={"zoo":"zoo","rabbitmq":"rabbitmq"},\
network="ccproj",restart_policy={"Name":"on-failure"},volumes = {'/var/run/docker.sock':{'bind':'/var/run/docker.sock'}}, name="slave" + str(time.time()))


@zookeepersession.zk.DataWatch('/workers/node')
def elect_leader(data,stat,event):
    print ("event received is %s", str(event))
    try:
        if (event.type=='DELETED'):
            if (zookeepersession.is_master()):
                pass
            t = Timer(10.0, create_slave_node)
    except Exception as ex:
        print(ex)
        pass

read_result = channel.queue_declare(queue='read_queue',)
write_result = channel.queue_declare(queue='write_queue',)
sync_result = channel.queue_declare(queue='sync_queue',)
r_queue = read_result.method.queue
s_queue = sync_result.method.queue

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

def read_from_db(body):
    body = json.loads(body)
    if body is None or "action" not in body:
        x={"res": "invalid request", "error": 400}
        return(json.dumps(x))
    
    action = body["action"]
    
    if action == "list_upcoming_ride":
        x={"res":db_list_ride(body)}
        return(json.dumps(x)) 

    elif action == "get_ride":
        x={"res":db_get_ride(body)}
        return(json.dumps(x)) 
    elif action == "get_user":
        x={"res": db_get_user(body)}
        return(json.dumps(x)) 
    elif action =="list_users":
        x={"res": db_list_users(body)}
        return(json.dumps(x)) 
    elif action =='num_ride':
        x={"res": db_num_rides(body)}
        return(json.dumps(x)) 
    else:
        raise BadRequest("unrecognized action %s" % (action))

def write_to_db(body):
    body = json.loads(body)
    if "action" not in body:
        raise BadRequest("action not passed")

    action = body["action"]
    try:
        if action == "add_user":
            db_add_user(body)
            x={"res": {}}
            return(json.dumps(x)) 

        elif action == "delete_user":
            db_delete_user(body)
            x={"res": {}}
            return(json.dumps(x)) 

        elif action == "add_ride":
            ride_id = db_create_ride(body)
            x={"res": {"ride_id": ride_id}}
            return(json.dumps(x)) 
        
        elif action == "delete_ride":
            db_delete_ride(body)
            x={"res": {}}
            return(json.dumps(x)) 
        
        elif action == "join_ride":
            db_join_ride(body)
            x={"res":{}}
            return(json.dumps(x)) 
        elif action == "delete_db":
            db_delete_db(body)
            x={"res":{}}
            return(json.dumps(x)) 
        else:
            raise BadRequest("unrecognized action %s" % (action))
    except BadRequest as ex:
        raise
    except Exception as ex:
        print(ex)
        raise BadRequest("invalid request")

def on_request_read_write(ch, method, props, body):
    try:
        if method.routing_key == 'read_queue':
            response = read_from_db(body)
        elif method.routing_key == 'write_queue':
            print('got write message')
            response = write_to_db(body)
            #ch.basic_publish(queue=s_queue, routing_key='sync_queue', body= body)

        print(response,method.routing_key)

        ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as ex:
        print(ex)
        desc = ex.description
        if ex.description is None:
            desc = "invalid request"
        response = json.dumps({"res": desc, "error": 400})
        print(response,method.routing_key)

        ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)


def on_request_sync(ch, method, props, body):
    if method.routing_key == 'sync_queue':
        response = write_to_db(body)
        print(response)

channel.basic_qos(prefetch_count=1)

if zookeepersession.is_master():
    print ("pid for master = %s" % (zookeepersession.PID))
    channel.basic_consume(queue='write_queue', on_message_callback=on_request_read_write, consumer_tag='master_write')

if not zookeepersession.is_master():
    print ("pid for slave = %s" % (zookeepersession.PID))
    channel.basic_consume(queue= r_queue, on_message_callback=on_request_read_write, consumer_tag='slave_read')
    channel.basic_consume(queue = s_queue, on_message_callback=on_request_sync, consumer_tag='slave_sync')

print(" [x] Awaiting Read Write requests")
# channel.start_consuming()
while True:
    connection.process_data_events()
