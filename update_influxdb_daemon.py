#!/usr/bin/python
import ConfigParser, os
import logging.handlers, logging.config
from datetime import datetime
import sys, time, threading, os, glob, logging, ow

import requests
from influxdb import InfluxDBClient
from influxdb.client import InfluxDBClientError
import pcd8544.lcd as lcd
import time
import RPi.GPIO as GPIO   #import the GPIO library
import Adafruit_DHT

# Sensor should be set to Adafruit_DHT.DHT11,
# Adafruit_DHT.DHT22, or Adafruit_DHT.AM2302.
dht11_sensor = Adafruit_DHT.DHT11
# Example using a Raspberry Pi with DHT sensor
# connected to GPIO23.
dht11_pin = 17
logging.config.fileConfig("updater.cfg")
logging.getLogger(__name__)

config = ConfigParser.ConfigParser()
config.readfp(open('updater.cfg'))
base_dir = config.get('main','base_dir')+"/"
raspiURL = config.get('main','raspiURL')
sleep = config.getint('main','sleep')

DBNAME = 'temps'

buzzer_pin = 5                   #set the buzzer pin variable to number 18
GPIO.setmode(GPIO.BCM)#Use the Broadcom method for naming the GPIO pins
GPIO.setup(buzzer_pin, GPIO.OUT)  #Set pin 18 as an output pin
GPIO.setwarnings(False)
def buzz(pitch, duration):   #create the function "buzz" and feed it the pitch and duration)
    period = 1.0 / pitch     #in physics, the period (sec/cyc) is the inverse of the frequency (cyc/sec)
    delay = period / 2     #calcuate the time for half of the wave
    cycles = int(duration * pitch)   #the number of waves to produce is the duration times the frequency
    for i in range(cycles):    #start a loop from 0 to the variable "cycles" calculated above
        GPIO.output(buzzer_pin, True)   #set pin 18 to high
        time.sleep(delay)    #wait with pin 18 high
        GPIO.output(buzzer_pin, False)    #set pin 18 to low
        time.sleep(delay)    #wait with pin 18 low
def startupbeep():
    i=200
    while i<=2000:
        buzz(i, 0.1)  #feed the pitch and duration to the function, "buzz"
        i+=200
def beeper():
    while True:
        buzz(2000,0.1)
        time.sleep(0.1)



def lcd_blink(text):
    i=10
    lcd.cls()
    lcd.locate(0,0)
    lcd.text(text)
    lcd.locate(0,1)
    while i<0:
       lcd.text("after %s sec" % (i))
       if i%2:
           lcd.backlight(1)
       else:
           lcd.backlight(0)
       i-=1
       time.sleep(1)

def value2lcd(date,id,desc,value):
    lcd.cls()
    lcd.locate(0,0)
    lcd.text(date)
    lcd.locate(0,1)
    lcd.text(id)
    lcd.locate(0,2)
    lcd.text(desc)
    lcd.locate(0,3)
    lcd.text("Temp: %s" % (value))
    lcd.locate(0,4)

def lcdstatusupdate(sensor_count,i):
    date = datetime.now()
    lcd.locate(3,0)
    lcd.text(date.strftime('%d/%m/%y'))
    lcd.locate(3,1)
    lcd.text(date.strftime('%H:%M:%S'))
    lcd.locate(3,2)
    lcd.text("sensr: %s" % sensor_count)
    lcd.locate(3,3)
    lcd.text("Next: %s" % i)
    lcd.locate(3,4)

class tmpclass(object):
    pass
def read_dht11():
    h = tmpclass()
    t = tmpclass()
    humidity, temperature = Adafruit_DHT.read_retry(dht11_sensor, dht11_pin)
    if humidity is not None and temperature is not None:
        h.address = "DHT11_humidity"
        h.value = humidity
        t.address = "DHT11_temp"
        t.value = temperature
        return h,t
    else:
       read_dht11()
def calc_power():
    p = tmpclass()
    pealevool = value = float(ow.Sensor('/28FF461F10140002').temperature11)
    tagasivool = value = float(ow.Sensor('/28FF981E10140071').temperature11)
    delta = abs(pealevool-tagasivool)
    power = delta*4.2*1.1 
    p.value = "%0.2f" % power
    p.address = "Power"
    return p


def daemon():
    client = InfluxDBClient('cms.emon.ee', 8086, 'USER', 'PASSWORD', DBNAME,timeout=30)
    ow.init('localhost:4304')
    lcd.init()
    logging.debug("Daemon starting")
    logging.debug("Create INFLUX database: " + DBNAME)
    errors = 0
    try:
        client.create_database(DBNAME)
    except InfluxDBClientError:
        logging.debug("%s DB already exist" % DBNAME)
        pass
    except:
        logging.exception("Error")
        lcd.text("Exception")
   # try:
   #     client.create_retention_policy('awesome_policy', '3d', 3, default=True)
   # except InfluxDBClientError:
   #     logging.debug("%s policy already exist" % DBNAME)
   #     pass

    
    while True:
        try:
            devices = ow.Sensor('/').sensorList()
            date = datetime.now()
            points=[]
            for o in read_dht11():
                devices.append(o)
            devices.append(calc_power())
            for sensor in devices:
                name = sensor.address
                try:
                    value = float(sensor.value)
                except:
                    value = float(ow.Sensor('/%s' % name).temperature11)
                desc = name
                json_body = {   
                       "time": date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                       "measurement": "rosma_temps",
                       "tags": {
                           "sensor": name,
                       },
                       "fields": {
                           "value": value
                       }
                   }
                points.append(json_body)
                value2lcd(date.strftime('%d/%m/%y %H:%M:%S'),name,desc,value)
                logging.debug(json_body)
            status=client.write_points(points)
            if status:
                lcd.text("Sent<-OK")
                logging.debug(status)
            else:
                lcd.text("Error!")
                logging.error(status)
            #Show status
            s=0
            lcd.cls()
            while s<sleep:
                lcdstatusupdate(len(devices),s)
                time.sleep(1)
                s+=1
        except:
                logging.exception("Error occurred %s" % sys.exc_info()[1])
                lcd.text("%s Exception!" % errors)
                time.sleep(1)
                if errors == 10:
                     lcd_blink("Rebooting!")
                     d = threading.Thread(name='beeper', target=beeper)
                     d.setDaemon(True)
                     d.start()
                     #os.system("reboot")
                     d.join()
                else:
                    errors += 1
    logging.debug("Daemon exiting")
    return(0)



if __name__ == "__main__":
    startupbeep()
    try:
        d = threading.Thread(name='daemon', target=daemon)
        d.setDaemon(True)
        d.start()
        d.join()
    except:
        logging.exception(error)
