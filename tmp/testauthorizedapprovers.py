#!/usr/bin/python

import csv, ldap, ConfigParser, MySQLdb, time, sys, os

cfg = ConfigParser.ConfigParser()
cfg.read('/opt/usermanager/etc/usermanager.ini')

approvers = cfg.get('approvers', 'approvers')

print approvers

approvers_list = approvers.split(",")

myusername = 'scaron'

user_is_authorized = False

for user in approvers_list:
    print user

    if user == myusername:
        print "Found authorized user"
        user_is_authorized = True

print str(user_is_authorized)

