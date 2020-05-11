import pika
from flask import Flask
from flask import request, abort, jsonify, render_template
import uuid
import json
port = 7000
app = Flask(__name__)


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

read_write = ReadWriteRequests()




@app.route("/api/v1/db/write", methods={'POST'})
def write():
    body = request.get_json()
    state = 'write'
    response = read_write.call(json.dumps(body),state)
    response = json.loads(response)
    print(response)
    return jsonify(response["res"])

@app.route("/api/v1/db/read", methods={'POST'})
def read():
    body = request.get_json()
    state = 'read'
    response = read_write.call(json.dumps(body),state)
    response = json.loads(response)
    print(response)    
    return jsonify(response["res"])









if __name__ == "__main__":
    app.run(port = port,debug=True)
