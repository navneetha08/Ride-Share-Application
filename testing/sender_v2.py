import pika
from flask import Flask
from flask import request, abort, jsonify, render_template
import uuid
import json
from flask import Response
import docker
port = 80
app = Flask(__name__)
import logging
from kazoo.client import KazooClient,KazooState
from timeloop import Timeloop
from datetime import timedelta
import time
from math import ceil
import requests as r
logging.basicConfig()

global db_read_count
db_read_count = 0

tl = Timeloop()
global conts
conts = 3

client = docker.from_env()

localhost_url = "http://34.203.18.244"

class ZookeeperOrch(object):
    def __init__(self):
        self.zk = KazooClient(hosts='zoo:2181')
        self.zk.start()
        self.zk.ensure_path('/workers')
        try:
            self.zk.create('/election/leader',makepath=True)
        except:
            pass
    
    def get_master_PID(self):
        try:
            master_data, master_stat = self.zk.get('/workers/master')
            return master_data
        except:
            return None

    def get_workers(self):
        worker_nodes = self.zk.get_children('/workers')
        worker_pid = [] 
        for i in worker_nodes:
            data,stat=self.zk.get('/workers/'+i)
            data = data.decode('utf-8')
            worker_pid.append(int(data))
        workers = sorted(worker_pid)
        return workers
    
    def get_highest_slave(self):
        workers = self.get_workers()
        slave = max(workers)
        slave = workers
        pid = self.get_master_PID()
        if (pid is not None):    
            if (slave != pid):
                return slave
        else: 
            return slave


class ReadWriteRequests(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rmq',heartbeat=0))

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
        print(self.response)
        return str(self.response)

zksession = ZookeeperOrch()

#takes care of scaling
@tl.job(interval=timedelta(seconds=120))
def scaling():
    global db_read_count
    print("in scaling function")
    no_of_slaves_reqd = ceil(db_read_count/20) 
    no_of_slaves_available = len(client.containers.list())-4
    print(no_of_slaves_reqd,no_of_slaves_available)
    db_read_count = 0
    while ((no_of_slaves_available>no_of_slaves_reqd) and (len(client.containers.list())-5>0)):
        body='' #Not sure of this part
        r.post("%s/api/v1/crash/slave" % (localhost_url), json = body)
        no_of_slaves_available = no_of_slaves_available - 1
        #add code to scale up
    while (no_of_slaves_available<no_of_slaves_reqd):
        #client = docker.from_env()
        c_name = "testing_worker_"+str(conts)+"_1"
        conts = conts + 1
        worker_cont=client.containers.run(image="slaves:latest",name=c_name,entrypoint="sh -c 'sleep 10 && python master_v4.py '"+c_name+"' && python db_op.py'",links={"zoo":"zoo","rmq":"rmq"},\
network="cloud",restart_policy={"Name":"on-failure"},detach=True,privileged=True)
#        pid = worker_cont.top()
#        worker_cont.exec_run('sh -c "sleep 20 && python master_v4.py"',environment={"PID":pid})
        no_of_slaves_avaliable = no_of_slaves_available + 1
# docker run -it --rm --network cloud -e 10 --entrypoint python master_v4.py slaves 
@zksession.zk.ChildrenWatch('/workers',send_event=True)
def availability(children,event):
    if(event!=None):
   	 if (event.type=='DELETED' or event.state=='EXPIRED_SESSION'):
        	if zksession.zk.exists('/workers/master'):
            		scaling()

read_write = ReadWriteRequests()
'''
for i in range(2):
        client = docker.from_env()
        worker_cont=client.containers.run(image='slaves:latest',entrypoint="sh -c 'while true; do : ;done'",links={'zookeeper':'zoo','rabbitmq':'rabbitmq'},\
network="cloud",restart_policy={"Name":"on-failure"},detach=True,privileged=True)
        pid = worker_cont.top()
        worker_cont.exec_run('sh -c "python master_v4.py"',environment={"PID":pid})
'''
tl.start()

@app.route("/api/v1/db/write", methods={'POST'})
def write():
    body = request.get_json()
    state = 'write'
    read_write.call(json.dumps(body),state)
    return str(200)

@app.route("/api/v1/db/read", methods={'POST'})
def read():
    body = request.get_json()
    state = 'read'
    global db_read_count
    db_read_count = db_read_count + 1
    response = read_write.call(json.dumps(body),state)
    response = json.loads(response)
    print(response)    
    return response

@app.route("/api/v1/crash/master", methods={'POST'})
def master_kill():
    l=[]
    master_id = zksession.get_master_PID()
    if (master_id is not None): 
        #client = docker.from_env()
        client.kill(master_id)
        l.append(str(master_id))
        return Response(json.dumps(l), status=200, mimetype='application/json')

@app.route("/api/v1/crash/slave", methods={'POST'})
def slave_kill():
    #client=docker.from_env()
    '''
    ids=[]
    for container in client.containers.list():
        ids.append(container.id)
    ids=sorted(ids)
    slave_to_kill=ids[-1]
    '''
    slave_to_kill = zksession.get_highest_slave()
    print(slave_to_kill)
    #if (slave_to_kill != None):
    l = client.containers.list()
    for container in l:
       # if(int(container.top()['Processes'][0][1])==int(slave_to_kill))
        pids.append(int(container.top()['Processes'][0][1]))
    mpid = max(pids)
    container = l[pids.index(mpid)]    
    container.kill()
    return Response(json.dumps(), status=200, mimetype='application/json')
    

@app.route("/api/v1/worker/list", methods={'GET'})
def list_cont():
    '''
    client = docker.from_env()
    list_workers=[]
    for container in client.containers.list():
        list_workers.append(container.id)
    '''
    list_workers = zksession.get_workers()
    return Response(json.dumps(list_workers), status=200, mimetype='application/json')




@app.route("/api/v1/db/clear", methods={'POST'})
def delete_db():
    body = {}
    body["action"] = "delete_db"
    response = r.post(url = "http://34.203.18.244/api/v1/db/write", json = body)
    return str(200)
	#if response.status_code != 201:
        #raise BadRequest("some error occurred")

if __name__ == "__main__":
    app.run(port = port,debug=True,host="0.0.0.0",use_reloader=True)

tl.stop()
