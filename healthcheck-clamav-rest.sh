#!/bin/bash

STATUSCODE=$(curl -L --silent --output /dev/null --write-out "%{http_code}" 127.0.0.1:8080)

if test $STATUSCODE -ne 200; then
    echo "FAILURE: Request failed with HTTP status code $STATUSCODE."
    exit 1
else 
    echo "SUCCESS: Endpoint responded with status code 200."
    exit 0
fi
