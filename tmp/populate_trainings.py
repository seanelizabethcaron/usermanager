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

local_curs = local_db.cursor()
query = 'SELECT serialnum, uniqname FROM users;'
local_curs.execute(query)
report = local_curs.fetchall()

# Connect to the MAIS LINC database
mais_dbase = pymssql.connect(server=mais_dbhost, user=mais_dbuser, password=mais_passwd, database=mais_db, port=mais_dbport)
mais_cursor = mais_dbase.cursor()

for username in report:

    # Serialnum is username[0] uniqname is username[1]

    # Determine DCE 101 completion status
    query = 'SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk AND b.Code in (\'DCE101\') and d.Username in (\'' + username[1] + '\');'

    mais_cursor.execute(query)
    result = mais_cursor.fetchone()

    if result == None:
        dce101_completed = 0
    else:
        dce101_completed = 1

    # Determine ITSE 106 completion status
    query = 'SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk AND b.Code in (\'ITS_ITSE106\') and d.Username in (\'' + username[1] + '\');'

    mais_cursor.execute(query)
    result = mais_cursor.fetchone()

    if result == None:
        itse106_completed = 0
    else:
        itse106_completed = 1

    # Populate these fields with sentinel values for existing accounts
    held_pending = 0
    send_reminder = 0
    held_since = '0000-00-00'

    if dce101_completed and itse106_completed:
        topmed_user = 1
    else:
        topmed_user = 0

    # Update the local database record
    query = 'INSERT INTO trainings (serialnum, topmed_user, dce101_comp, itse106_comp, held_pending, held_since, send_reminder) VALUES (' + str(username[0]) + ', ' + str(topmed_user) + ', ' + str(dce101_completed) + ', ' + str(itse106_completed) + ', ' + str(held_pending) + ', \'' + held_since + '\', ' + str(send_reminder) + ');'
    local_curs.execute(query)

local_db.commit()
    
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

# ITSE106 or DCE101

#
# If the user has completed DCE101, the query will return a string like:
#
# (u'42390493', u'SCARON', u'DCE101', u'DCE101 Archive Access and Compliance:
# Handling Sensitive Institutional Data at U-M', None, datetime.datetime(2018
# , 2, 21, 21, 14, 28, 410000))
#
# If the user has not completed DCE101, the query will return None
#


