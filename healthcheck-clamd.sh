#!/usr/bin/env bash

if clamdscan /eicar.com | grep -q 'Infected files: 1'; then
    echo 'SUCCESS: clamd running successfully'
    exit 0
else
    echo 'FAILURE: clamd not running'
    exit 1
fi
