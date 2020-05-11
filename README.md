# CCScam
Configuration
For this project, we have used a Load Balancer and EC2 Linux instances from AWS Enterprises.
This project has been implemented in phases
Phase 1:
A monolithic service consisting of users, rides and database APIs using flask. Our database is sqlite3 based.
Phase 2:
The monolithic service has been split into rides and users where each microservice has been containerized with its own database. Database accesses are also made across containers through a docker bridge network
We have implemeneted three microservices: rides, users and database.
The rides and users micro
