#!/usr/bin/env bash

set -e
export PYTHONPATH=/celery-worker/lib
HOSTNAME="$(hostname -f)"
if celery -A chowder status | grep -q "${POD_NAME:-$HOSTNAME}"':.*OK'; then
    echo 'SUCCESS: Celery worker is running successfully'
    exit 0
else
    echo 'FAILURE: Celery worker has failed'
    exit 1
fi
