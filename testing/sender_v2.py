import pika
from flask import Flask
from flask import request, abort, jsonify, render_template
import uuid
import json
from flask import Response
import docker
port = 7000
app = Flask(__name__)
import logging
from kazoo.client import KazooClient,KazooState
from timeloop import Timeloop
from datetime import timedelta
import time
from math import ceil

logging.basicConfig()

global db_read_count
db_read_count = 0

tl = Timeloop()

class ZookeeperOrch(object):
    def __init__(self):
        self.zk = KazooClient(hosts='zoo:2181')
        self.zk.start()
        self.zk.ensure_path('/workers')
        self.zk.create('/election/leader',makepath=True)
    
    def get_master_PID(self):
        try:
            master_data, master_stat = self.zk.get('/workers/master')
            return master_data
        except NoNodeError:
            return None

    def get_workers(self):
        worker_nodes = self.zk.get_children('/workers',include_data=True)
        worker_pid = []
        for i in worker_nodes:
            worker_pid.append(i[1])
        workers = sorted.worker_pid
        return workers
    
    def get_highest_slave(self):
        workers = self.get_workers()
        slave = max(workers)
        pid = self.get_master_PID()
        if (pid != None):    
            if (slave != pid):
                return slave


class ReadWriteRequests(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))

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
            self.channel.basic_publish(
            exchange='',
            routing_key='write_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=bod)            
        while self.response is None:
            self.connection.process_data_events()
        return str(self.response)

zksession = ZookeeperOrch()

#takes care of scaling
@tl.job(interval=timedelta(seconds=120))
def scaling():
    global db_read_count
    no_of_slaves_reqd = ceil(db_read_count/20) 
    no_of_slaves_available = len(zksession.get_workers)-1
    db_read_count = 0
    while (no_of_slaves_available>no_of_slaves_reqd):
        body='' #Not sure of this part
        r.post("%s/api/v1/crash/slave" % (localhost_url), json = body)
        #add code to scale up

@zksession.zk.ChildrenWatch('/workers',send_event=True)
def availability(children,event):
    if (event.type=='DELETED' or event.state=='EXPIRED_SESSION'):
        if zksession.zk.exists('/workers/master'):
            scaling()

read_write = ReadWriteRequests()
tl.start()

@app.route("/api/v1/db/write", methods={'POST'})
def write():
    body = request.get_json()
    state = 'write'
    response = read_write.call(json.dumps(body),state)
    response = json.loads(response)
    print(response)
    return Response(jsonify(response["res"]), status=200, mimetype='application/json')

@app.route("/api/v1/db/read", methods={'POST'})
def read():
    body = request.get_json()
    state = 'read'
    global db_read_count
    db_read_count = db_read_count + 1
    response = read_write.call(json.dumps(body),state)
    response = json.loads(response)
    print(response)    
    return Response(jsonify(response["res"]), status=200, mimetype='application/json')



@app.route("/api/v1/crash/master", methods={'POST'})
def master_kill():
    l=[]
    master_id = zksession.get_master_PID()
    if (master_id is not None): 
        client = docker.from_env()
        client.kill(master_id)
        l.append(str(master_id))
        return Response(json.dumps(l), status=200, mimetype='application/json')

@app.route("/api/v1/crash/slave", methods={'POST'})
def slave_kill():
    client=docker.from_env()
    '''
    ids=[]
    for container in client.containers.list():
        ids.append(container.id)
    ids=sorted(ids)
    slave_to_kill=ids[-1]
    '''
    slave_to_kill = zksession.get_highest_slave()
    if (slave_to_kill != None):
        for container in client.containers.list():
            if(container.id==slave_to_kill):
                container.kill()
    return Response(json.dumps(list(str(slave_to_kill))), status=200, mimetype='application/json')
    

@app.route("/api/v1/worker/list", methods={'POST'})
def list_cont():
    '''
    client = docker.from_env()
    list_workers=[]
    for container in client.containers.list():
        list_workers.append(container.id)
    '''
    list_workers = zksession.get_workers
    return Response(json.dumps(list_workers), status=200, mimetype='application/json')



if __name__ == "__main__":
    app.run(port = port,debug=True)

tl.stop()
