import pika
from flask import Flask
from flask import request, abort, jsonify, render_template
import uuid
import json
from flask import Response
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import NotFound
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import MethodNotAllowed
import docker
import logging
from kazoo.client import KazooClient,KazooState
from datetime import timedelta
import time
import requests
from math import ceil
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig()
port = 80
app = Flask(__name__)

global db_read_count
db_read_count = 0

client = docker.from_env()


class ZooKeeperConnect:
    def __init__(self):
        self.zk = KazooClient(hosts='zoo:2181')
        self.zk.start()
        self.zk.ensure_path('/workers')

    def get_master_node_pid(self):
        return self.zk.get(self.zk.get_children('/workers/master')[0])[0].decode('utf-8')

    def get_workers(self):
        self.zk.ensure_path('/workers/node')
        return self.zk.get_children('/workers/node')

zookeepersession = ZooKeeperConnect()

class ReadWriteRequests(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters('rabbitmq'))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, bod,state):
        print (bod)
        self.response = None
        self.corr_id = str(uuid.uuid4())
        if state=='read':
            self.channel.basic_publish(
            exchange='',
            routing_key='read_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=bod)
            print("sent")
        elif state=='write':
            print('sending write request...')
            print('Params:')
            print('reply_to:', repr(self.callback_queue))
            print('correlation_id:', repr(self.corr_id))
            self.channel.basic_publish(
            exchange='',
            routing_key='write_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
             ),
            body=bod)            
            print('sent message; polling for response...')
        while self.response is None:
            self.connection.process_data_events()
        print('Reponse:', self.response)
        return self.response


def create_slave_node():
    print ("creating new slave node")
    worker_cont=client.containers.run(image="slave:latest", command='sh -c "python master_v4.py"',links={"zoo":"zoo","rabbitmq":"rabbitmq"},\
network="ccproj",restart_policy={"Name":"on-failure"},volumes = {'/var/run/docker.sock':{'bind':'/var/run/docker.sock'}}, name="slave"+ str(time.time()), detach=True)

#takes care of scaling
'''
def scaling():
    create_slave_node()
'''

#takes care of scaling
def scaling():
    global db_read_count
    no_of_slaves_reqd = ceil(db_read_count/20)
    if no_of_slaves_reqd == 0:
        no_of_slaves_reqd = 1
    no_of_slaves_available = len(zookeepersession.get_workers())
    print("in scaling function reqd: %s available : %s" %( str(no_of_slaves_reqd), str(no_of_slaves_available) ))
    db_read_count = 0
    localhost_url = "127.0.0.1:80"
    '''
    while (no_of_slaves_available>no_of_slaves_reqd):
        body={} #Not sure of this part
        requests.post("%s/api/v1/crash/slave" % (localhost_url), json = json.dumps(body))
        no_of_slaves_available = no_of_slaves_available - 1;
        #add code to scale up
    '''
    while (no_of_slaves_available<no_of_slaves_reqd):
        print("in scaling while loop function reqd: %s available : %s" %( str(no_of_slaves_reqd), str(no_of_slaves_available) ))
        create_slave_node()
        no_of_slaves_available = no_of_slaves_available + 1


@app.route("/api/v1/db/rep", methods={'GET'})
def get_file():
    users_file=open("users.txt","r")
    rides_file=open("rides.txt","r")
    users_data=users_file.readlines()
    rides_data=rides_file.readlines()
    x={"userdata":users_data,"ridesdata":rides_data}
    return Response(json.dumps(x) ,status=200, mimetype='application/json')

@app.route("/api/v1/db/write", methods={'POST'})
def write():
    body = request.get_json()
    state = 'write'
    read_write = ReadWriteRequests()
    response = read_write.call(json.dumps(body),state)
    response = json.loads(response)
    print(response)
    if ("error" in response):
        raise BadRequest(response["res"])
    return Response(json.dumps(response["res"]), status=200, mimetype='application/json')

@app.route("/api/v1/db/read", methods={'POST'})
def read():
    body = request.get_json()
    state = 'read'
    global db_read_count
    db_read_count = db_read_count + 1
    read_write = ReadWriteRequests()
    response = read_write.call(json.dumps(body),state)
    response = json.loads(response)
    print(response) 
    if ("error" in response):
        raise BadRequest(response["res"])
    return Response(json.dumps(response["res"]), status=200, mimetype='application/json')

@app.route("/api/v1/crash/master", methods={'POST'})
def master_kill():
    l=client.container.list()[3:]
    ids=[]
    for i in l:
        id=i.top()
        ids.append(id)
    master_id = min(ids)
    l[ids.index(master_id)].kill()
    return Response(json.dumps(master_id), status=200, mimetype='application/json')

@app.route("/api/v1/crash/slave", methods={'POST'})
def slave_kill():
    l=client.container.list()
    ids=[]
    for i in l:
        id=i.top()
        ids.append(id)
    slave_id = max(ids)
    l[ids.index(master_id)].kill() 
    return Response(json.dumps(list(str(slave_to_kill))), status=200, mimetype='application/json')
    

@app.route("/api/v1/worker/list", methods={'GET'})
def list_cont():
    workers = [i.top() for i in client.containers.list()[3:]]
    list_workers = sorted(workers)
    return Response(json.dumps(list_workers), status=200, mimetype='application/json')



if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    job = scheduler.add_job(scaling, 'interval', minutes=1)
    scheduler.start()
    app.run(port = port,debug=True,host="0.0.0.0",threaded=True,use_reloader=False)
