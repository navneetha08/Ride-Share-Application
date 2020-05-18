# CCScam
A cloud based RideShare application, meant to facilitate booking rides.
For this project, we have used a Load Balancer and EC2 Linux instances from AWS Enterprises.
This project has been implemented in phases
## Phase 1:
A monolithic service consisting of users, rides and database APIs using flask. Our database is sqlite3 based.
#### To execute this application:
In CCProject/assignment1
```
sudo python main.py
```
## Phase 2:
The monolithic service has been split into rides and users where each microservice has been containerized with its own database. Database accesses are also made across containers through a docker bridge network.
#### To execute this application:
In CCProject/assignment2
```
sudo docker-compose build
sudo docker-compose up -d
```
## Phase 3:
The microservices have been shifted to separate instances and now the API calls are sent to these services via a Load Balancer. The database calls are made through a docker overlay network.
#### To execute this application:
In CCProject/assignment3/ride/app on the rides instance
```
sudo docker build --tag rides .
sudo docker run rides
```
In CCProject/assignment3/user/app on the users instance
```
sudo docker build --tag users .
sudo docker run users
```
## Final Phase:
We have implemeneted three microservices: rides, users and database.
API calls are sent to the users and rides services via a Load Balancer. The rides and users now make calls to the database microservice. The orchestrator sends those requests to workers via queues. After receiving response from queue, it sends reponse to the service that made the API call. Master workers perform reads and slave workers perform writes. Fault-tolerance and availability have been taken care of. 
#### To execute this application:
In the rides instance
```
sudo docker build --tag rides .
sudo docker run -p 80:80 rides
```
In the users instance
```
sudo docker build --tag users .
sudo docker run -p 80:80 users
```
In the orchestrator instance:
```
bash run.sh
```

