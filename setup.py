#!/usr/bin/env python2

import ConfigParser
import subprocess
import os
import subprocess
from subprocess import Popen

def checkService(service):
    user = (ConfigSectionMap(service)['user'])
    password = (ConfigSectionMap(service)['password'])
    print user
    print password
    if not user and not password: 
       return 
    DBConfig = ConfigParser.ConfigParser()
    if service == "Box":
        DBConfig.read("/usr/lib/python2.7/site-packages/CloudFusion-5.10.16-py2.7.egg/cloudfusion/config/Webdav.ini")
    else:
        DBConfig.read("/usr/lib/python2.7/site-packages/CloudFusion-5.10.16-py2.7.egg/cloudfusion/config/"+service+".ini")
    DBConfig.set('auth','user',user)
    DBConfig.set('auth','password',password)
    if service == "Box":
        DBConfig.set('auth','url',"https://dav.box.com/dav")
    with open('./'+service+'.ini', 'w') as configfile:
        DBConfig.write(configfile)

def checkSudo():
    user = os.getuid()
    if user != 0:
        print "This program requires root privileges.  Run as root using 'sudo'."
        sys.exit()

def checkCloudFusion():
    try:
        devnull = open(os.devnull)
        subprocess.Popen(["cloudfusion"], stdout=devnull, stderr=devnull).communicate()
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            print "CloudFusion not installed"
            Popen(["git","clone","git://github.com/joe42/CloudFusion.git","/tmp/CloudFusion"])
            Popen(["python2","/tmp/CloudFusion/setup.py"])
            return False
    print "CloudFusion installed"
    #Popen(["git","clone","git://github.com/joe42/CloudFusion.git","/tmp/CloudFusion"])
    #Popen(["python2","/tmp/CloudFusion/setup.py"])
    return True

def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1

Config = ConfigParser.ConfigParser()
Config.read("ucs.conf")
checkSudo()
checkService("Dropbox")
checkService("Google")
checkService("Box")

