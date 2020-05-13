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
from timeloop import Timeloop
from datetime import timedelta
import time
from math import ceil

logging.basicConfig()
port = 80
app = Flask(__name__)

global db_read_count
db_read_count = 0

tl = Timeloop()

'''
class ZookeeperOrch(object):
    def __init__(self):
        self.zk = KazooClient(hosts='zookeeper:2181')
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
'''

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

client = docker.from_env()

#zksession = ZookeeperOrch()

#takes care of scaling
@tl.job(interval=timedelta(seconds=120))
def scaling():
    global db_read_count
    print("in scaling function")
    '''
    no_of_slaves_reqd = ceil(db_read_count/20) 
    no_of_slaves_available = len(zksession.get_workers())-1
    db_read_count = 0
    while (no_of_slaves_available>no_of_slaves_reqdi:
        body='' #Not sure of this part
        r.post("%s/api/v1/crash/slave" % (localhost_url), json = body)
        #add code to scale up
    while (no_of_slaves_available<no_of_slaves_reqd):
        client = docker.from_env()
        worker_cont=client.containers.run(image="slaves:latest",entrypoint="sh -c 'while true;do : ;done'",links={"zoo":"zoo","rabbitmq":"rabbitmq"},\
network="ccproj",restart_policy={"Name":"on-failure"},detach=True,privileged=True,cpu_shares=96)
        pid = worker_cont.top()
        worker_cont.exec_run('sh -c "sleep 20 && python master_v4.py"',environment={"PID":pid})
        no_of_slaves_avaliable = no_of_slaves_available + 1


@zksession.zk.ChildrenWatch('/workers',send_event=True)
def availability(children,event):
    if(event!=None):
   	 if (event.type=='DELETED' or event.state=='EXPIRED_SESSION'):
        	if zksession.zk.exists('/workers/master'):
            		scaling()
for i in range(2):
        print('starting slave:', i)
        worker_cont=client.containers.run(image='slaves:latest',entrypoint="sh -c 'master_v4.py'",links={'zoo':'zoo','rabbitmq':'rabbitmq'},\
network="ccproj",restart_policy={"Name":"on-failure"},detach=True,privileged=True, cpu_shares=96)
        # pid = worker_cont.top()['Processes'][0][-1]
        # worker_cont.exec_run('sh -c "master_v4.py"',environment={"PID":pid})
'''
tl.start()

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
    l=client.container.list()[3:]
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
    app.run(port = port,debug=True,host="0.0.0.0",use_reloader=True,threaded=True)
    tl.stop()

