#!/bin/bash

docker compose up --build -d

# Wait for the MongoDB container to be ready
sleep 5
 

gnome-terminal -- bash -c "
./mvnw spring-boot:run
exec bash
"