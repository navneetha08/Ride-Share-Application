
# CCScam
A cloud based RideShare application, meant to facilitate booking rides.
For this project, we have used a Load Balancer and EC2 Linux instances from AWS Enterprises.
This project has been implemented in phases
## Phase 1:
A monolithic service consisting of users, rides and database APIs using flask. Our database is sqlite3 based.
To execute this application:
Go to CCScam->assignment1
`sudo python main.py`
## Phase 2:
The monolithic service has been split into rides and users where each microservice has been containerized with its own database. Database accesses are also made across containers through a docker bridge network.
## Phase 3:
The microservices have been shifted to separate instances and now the API calls are sent to these services via a Load Balancer. The database calls are made through a docker overlay network.
## Final Phase:
We have implemeneted three microservices: rides, users and database.
API calls are sent to the users and rides services via a Load Balancer. The rides and users now make calls to the database microservice.
