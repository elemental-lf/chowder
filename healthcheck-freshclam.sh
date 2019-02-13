#!/usr/bin/env bash

if freshclam | grep -q 'bytecode.* is up to date'; then
    echo 'SUCCESS: freshclam running successfully'
    exit 0
else
    echo 'FAILURE: freshclam not running'
    exit 1
fi
