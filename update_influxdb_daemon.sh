#!/bin/bash

cd /srv/data/logger/updater
daemon_name=update_influxdb_daemon
if [ ! -d /tmp/updater ]
then
mkdir /tmp/updater
fi

if [ -f /tmp/updater/$daemon_name.lock ] ; then
    exit 0
fi

touch /tmp/updater/$daemon_name.lock

/usr/bin/python $daemon_name.py | tee /dev/null

rm -f /tmp/updater/$daemon_name.lock
