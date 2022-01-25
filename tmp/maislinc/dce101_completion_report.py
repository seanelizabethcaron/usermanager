#!/usr/bin/python

import csv, ldap, ConfigParser, MySQLdb, time, sys, os,pymssql

cfg = ConfigParser.ConfigParser()
cfg.read('/opt/usermanager/etc/usermanager.ini')

dbuser = cfg.get('database', 'user')
dbpass = cfg.get('database', 'passwd')
dbname = cfg.get('database', 'db')
dbhost = cfg.get('database', 'host')
audit = cfg.getboolean('logging', 'audit')
debug = cfg.getboolean('logging', 'debug')
audit_log_file = cfg.get('logging', 'auditlog')
debug_log_file = cfg.get('logging', 'debuglog')

mais_dbhost = ''
mais_dbuser = ''
mais_passwd = ''
mais_dbport = ''
mais_db = ''

# Get list of users to check from our local DB

# Connect to the database
local_db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

local_curs = local_db.cursor()
query = 'SELECT uniqname FROM users WHERE approved = 1 AND locked = 0 AND expired = 0;'
local_curs.execute(query)
report = local_curs.fetchall()

# Connect to the MAIS LINC database
mais_db = pymssql.connect(server=mais_dbhost, user=mais_dbuser, password=mais_passwd, database=mais_db, port=mais_dbport)
mais_cursor = mais_db.cursor()

for uniqname in report:
    query = 'SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk AND b.Code in (\'DCE101\') and d.Username in (\'' + uniqname[0] + '\');'

    mais_cursor.execute(query)
    result = mais_cursor.fetchone()

    if result == None:
        print uniqname[0] + ' DCE101 NOT COMPLETED'
    else:
        print uniqname[0] + ' DCE101 WAS COMPLETED'


#
# According to ITS support:
# The query that I built to pull the data in the spreadsheet is below. Once you have the
# ID and password you should be able to use it to run this query for whatever course code(s)
# (b.Code) or uniqname(s) (d.Username) that you'd like.
#
# SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt
# FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE
# c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk and
# b.Code in ('DCE101') and d.Username in ('SCARON');
#

# ITS_ITSE106 or DCE101

#
# If the user has completed DCE101, the query will return a string like:
#
# (u'42390493', u'SCARON', u'DCE101', u'DCE101 Archive Access and Compliance:
# Handling Sensitive Institutional Data at U-M', None, datetime.datetime(2018
# , 2, 21, 21, 14, 28, 410000))
#
# If the user has not completed DCE101, the query will return None
#

