#!/usr/bin/env bash

function process_file() {
    if [[ -n $1 ]]; then
        local SETTING_LIST=$(echo "$1" | tr ',' '\n' | grep "^[A-Za-z][A-Za-z]*=.*$")
        local SETTING

        for SETTING in ${SETTING_LIST}; do
            # Remove any existing copies of this setting.  We do this here so that
            # settings with multiple values (e.g. ExtraDatabase) can still be added
            # multiple times below
            local KEY=${SETTING%%=*}
            sed -i $2 -e "/^${KEY} /d"
        done

        for SETTING in ${SETTING_LIST}; do
            # Split on first '='
            local KEY=${SETTING%%=*}
            local VALUE=${SETTING#*=}
            echo "${KEY} ${VALUE}" >> "$2"
        done
    fi
}

if [ $# != 1 -o "$1" == "help" ];
then
    1>&2 cat <<EOF
    Please run this image with one of these commands:

    clamd           Run the ClamAV scanning daemon
    freshclam       Run the ClamAV update daemon
    rest            Run the ClamAV REST API daemon
    celery-worker   Run the Chowder Celery worker
EOF
    exit 64 # EX_USAGE
fi

COMMAND=$1
case $COMMAND in
    clamd)
        process_file "${CLAMD_SETTINGS_CSV}" /usr/local/etc/clamd.conf
        exec /tini -- /usr/local/sbin/clamd
    ;;
    freshclam)
        process_file "${FRESHCLAM_SETTINGS_CSV}" /usr/local/etc/freshclam.conf
        exec /tini -- /usr/local/bin/freshclam -d
    ;;
    rest)
        cd /clamav-rest
        exec /tini -- /usr/bin/java -jar clamav-rest-*.jar \
                        --clamd.host=127.0.0.1 --clamd.port=3310 \
                        --clamd.maxfilesize=4000MB --clamd.maxrequestsize=4000MB
    ;;
    celery-worker)
        export PYTHONPATH=/celery-worker/lib
        exec /tini -- /usr/local/bin/celery worker --loglevel=INFO --task-events \
                        --concurrency=1 -n "${POD_NAME:-%h}" -A chowder
    ;;
    *)
        echo 'Unknown command. Valid commands are "clamd", "freshclam", "rest" and "celery-worker".' 1>&2
        exit 64 # EX_USAGE
    ;;
esac

# Not reached
exit 0
