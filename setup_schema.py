#!/usr/bin/python3

#
# Requires packages: python3-ldap, python3-mysqldb
#

import os,csv,ldap,configparser,MySQLdb,time,sys

cfg = configparser.ConfigParser()
cfg.read('/opt/usermanager/etc/usermanager.ini')

dbuser = cfg.get('database', 'user')
dbpass = cfg.get('database', 'passwd')
dbname = cfg.get('database', 'db')
dbhost = cfg.get('database', 'host')
audit = cfg.getboolean('logging', 'audit')
debug = cfg.getboolean('logging', 'debug')
audit_log_file = cfg.get('logging', 'auditlog')
debug_log_file = cfg.get('logging', 'debuglog')

# Set umask such that both root and www-data can write to logfiles
os.umask(0o011)

if debug:
    debuglog = open(debug_log_file, 'a+')

if audit:
    auditlog = open(audit_log_file, 'a+')

# Connect to the database
db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

print '*** User Manager DB schema setup utility ***\n'

print 'Creating users table ...\n'

# Create users table
curs = db.cursor()
query = 'CREATE TABLE users (serialnum integer NOT NULL AUTO_INCREMENT PRIMARY KEY, uniqname varchar(16), uidnumber integer, firstname varchar(64), lastname varchar(64), emailaddress varchar(128), title varchar(128), startdate varchar(16), enddate varchar(16), approver varchar(16), requestor varchar(16), reason varchar(255), role varchar(64), approved boolean, rejected boolean, created boolean, expired boolean, locked boolean, reactivate boolean);'
curs.execute(query)
db.commit()

print 'Users table created\n'
print 'Creating groups table ...\n'

# Create groups table
curs = db.cursor()
query = 'CREATE TABLE groups (serialnum integer NOT NULL PRIMARY KEY, memberof varchar(1024));'
curs.execute(query)
db.commit()

print 'Groups table created\n'
print 'Creating homes table ...\n'

# Create homes table
curs = db.cursor()
query = 'CREATE TABLE homes (serialnum integer NOT NULL PRIMARY KEY, host varchar(64), path varchar(128), created boolean);'
curs.execute(query)
db.commit()

print 'Homes table created\n'
print 'Creating trainings table ...\n'

# Create trainings table
curs = db.cursor()
query = 'CREATE TABLE trainings (serialnum integer NOT NULL PRIMARY KEY, dce101_comp boolean, itse106_comp boolean, held_pending boolean, held_since varchar(16), send_reminder boolean);'
curs.execute(query)
db.commit()

print 'Trainints table created\n'

print 'User Manager DB schema setup complete!\n'

