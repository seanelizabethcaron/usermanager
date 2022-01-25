#!/usr/bin/python

import csv, ldap, ConfigParser, MySQLdb, time, sys, os, pymssql, datetime

cfg = ConfigParser.ConfigParser()
cfg.read('/opt/usermanager/etc/usermanager.ini')

dbuser = cfg.get('database', 'user')
dbpass = cfg.get('database', 'passwd')
dbname = cfg.get('database', 'db')
dbhost = cfg.get('database', 'host')

mais_dbhost = ''
mais_dbuser = ''
mais_passwd = ''
mais_dbport = ''
mais_db = ''

# Get list of users to check from our local DB

# Connect to the database
local_db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

serialnum = 100

local_curs = local_db.cursor()
query = 'SELECT held_pending FROM trainings WHERE serialnum = ' + str(serialnum) + ';'
local_curs.execute(query)
held_pending = local_curs.fetchone()

print held_pending

print held_pending[0]

if held_pending[0]:
    print 'Held_pending is TRUE\n'
else:
    print 'Held_pending is FALSE\n'

