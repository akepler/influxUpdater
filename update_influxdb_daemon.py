#!/usr/bin/python
import ConfigParser, os
import logging.handlers, logging.config
from datetime import datetime
import sys, time, threading, os, glob, logging, ow

import requests
import simplejson as json

from influxdb import InfluxDBClient

from influxdb.client import InfluxDBClientError


logging.config.fileConfig("updater.cfg")
logging.getLogger(__name__)

config = ConfigParser.ConfigParser()
config.readfp(open('updater.cfg'))
base_dir = config.get('main','base_dir')+"/"
raspiURL = config.get('main','raspiURL')
sleep = config.getint('main','sleep')

DBNAME = 'temps'


def daemon():

    client = InfluxDBClient('cms.emon.ee', 8086, 'USER', 'PASSWORD', DBNAME)
    ow.init('localhost:4304')
    logging.debug("Daemon starting")
    logging.debug("Create INFLUX database: " + DBNAME)
    errors = 0
    try:
        client.create_database(DBNAME)
    except InfluxDBClientError:
        logging.debug("%s DB already exist" % DBNAME)
        pass
   # try:
   #     client.create_retention_policy('awesome_policy', '3d', 3, default=True)
   # except InfluxDBClientError:
   #     logging.debug("%s policy already exist" % DBNAME)
   #     pass

    
    while True:
        
        try:
            fpid = os.fork()
            if fpid==0:
                os.setsid()
                devices = ow.Sensor('/').sensorList()
                series=[]
                for sensor in devices:
                    name = sensor.address
                    value = float(ow.Sensor('/%s' % name).temperature11)
                    desc = name
                    date = datetime.now()
                    
                    json_body = [
                       {
                           "measurement": "rosma_temps",
                           "tags": {
                               "sensor": name,
                           },
                           "time": date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                           "fields": {
                               "value": value
                           }
                       }
                    ]
                    logging.debug(client.write_points(json_body))
                    logging.debug(json_body)

                time.sleep(sleep)
            else:
                os._exit(0)
        except:
                logging.debug("Error occurred %s" % sys.exc_info()[1])
                time.sleep(sleep)
                if errors == 10:
                     os.system("reboot")
                else:
                    errors += 1
    logging.debug("Daemon exiting")
    return(0)



if __name__ == "__main__":
    d = threading.Thread(name='daemon', target=daemon)
    d.setDaemon(True)
    d.start()
    sys.exit(d.join())
