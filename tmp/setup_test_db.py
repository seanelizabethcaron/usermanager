#!/usr/bin/python

import csv, ldap, ConfigParser, MySQLdb, time, sys

cfg = ConfigParser.ConfigParser()
cfg.read('/opt/usermanager/etc/usermanager.ini')

dbuser = cfg.get('database', 'user')
dbpass = cfg.get('database', 'passwd')

dbname = 'usermanager_test'

dbhost = cfg.get('database', 'host')
audit = cfg.getboolean('logging', 'audit')
debug = cfg.getboolean('logging', 'debug')
audit_log_file = cfg.get('logging', 'auditlog')
debug_log_file = cfg.get('logging', 'debuglog')

if debug:
    debuglog = open(debug_log_file, 'a+')

if audit:
    auditlog = open(audit_log_file, 'a+')

# Connect to the database
db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

print '*** User Manager TEST DB schema setup and data loader utility ***\n'

print 'Creating users table ...\n'

# Create users table
curs = db.cursor()
query = 'CREATE TABLE users (serialnum integer NOT NULL AUTO_INCREMENT PRIMARY KEY, uniqname varchar(16), uidnumber integer, firstname varchar(64), lastname varchar(64), emailaddress varchar(128), title varchar(128), startdate varchar(16), enddate varchar(16), approver varchar(16), requestor varchar(16), reason varchar(255), role varchar(64), approved boolean, rejected boolean, created boolean, expired boolean, locked boolean, reactivate boolean);'
curs.execute(query)
db.commit()

# Create some fake requests
curs = db.cursor()
query = 'INSERT INTO users (uniqname,uidnumber,firstname,lastname,emailaddress,title,startdate,enddate,approver,requestor,reason,role,approved,rejected,created,expired,locked,reactivate) VALUES (\'' + 'cdobski' + '\',' + '99376625' + ',\'' + 'Chrissy' + '\',\'' + 'Dobski' + '\',\'' + 'cdobski@umich.edu' + '\',\'' + 'Administrative Specialist' + '\',\'' + '2018-04-01' + '\',\'' + '2025-04-01' + '\',\'' + 'scaron' + '\',\'' + 'scaron' + '\',\'' + 'Testing' + '\',\'' + 'user' + '\',0,0,0,0,0,0);'
curs.execute(query)
db.commit()

print 'Users table created\n'
print 'Creating groups table ...\n'

# Create groups table
curs = db.cursor()
query = 'CREATE TABLE groups (serialnum integer NOT NULL PRIMARY KEY, memberof varchar(1024));'
curs.execute(query)
db.commit()

curs = db.cursor()
query = 'INSERT INTO groups (serialnum, memberof) VALUES (1, \'statgen-users\');'
curs.execute(query)
db.commit()

print 'Groups table created\n'
print 'Creating homes table ...\n'

# Create homes table
curs = db.cursor()
query = 'CREATE TABLE homes (serialnum integer NOT NULL PRIMARY KEY, host varchar(64), path varchar(128), created boolean);'
curs.execute(query)
db.commit()

curs = db.cursor()
query = 'INSERT INTO homes (serialnum, host, path, created) VALUES (1, \'dumbo\', \'/net/dumbo/home/cdobski\', 0);'
curs.execute(query)
db.commit()

print 'Homes table created\n'
print 'User Manager TEST DB schema setup and data load complete!\n'

