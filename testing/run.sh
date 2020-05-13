#!/bin/bash

docker system prune -f
docker network create ccproj
docker-compose up --build
