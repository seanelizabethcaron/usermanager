#!/usr/bin/python3

import csv, ldap, configparser, MySQLdb, time, sys, os, pymssql, datetime

cfg = configparser.ConfigParser()
cfg.read('/opt/usermanager/etc/usermanager.ini')

dbuser = cfg.get('database', 'user')
dbpass = cfg.get('database', 'passwd')
dbname = cfg.get('database', 'db')
dbhost = cfg.get('database', 'host')

mais_dbhost = cfg.get('maislinc', 'mais_dbhost')
mais_dbuser = cfg.get('maislinc', 'mais_dbuser')
mais_passwd = cfg.get('maislinc', 'mais_passwd')
mais_dbport = cfg.get('maislinc', 'mais_dbport')
mais_db = cfg.get('maislinc', 'mais_db')

# Define field widths
width_firstname = 25
width_lastname = 30
width_uniqname = 16
width_dce101 = 5
width_bulkdata = 5
width_itse106 = 5

# Print header
print(f"{'Lastname':<{width_lastname}} {'Firstname':<{width_firstname}} {'Uniqname':<{width_uniqname}} {'DCE':<{width_dce101}} {'BULK':<{width_bulkdata}} {'ITSE':<{width_itse106}}")
print("-" * (width_lastname + width_firstname + width_uniqname + width_dce101 + width_bulkdata + width_itse106 + 4))

# Get list of users to check from our local DB

# Connect to the database
local_db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

local_curs = local_db.cursor()
#query = 'SELECT serialnum, uniqname, firstname, lastname FROM users order by lastname asc limit 10;'
query = 'SELECT serialnum, uniqname, firstname, lastname FROM users order by lastname asc;'
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

    # Determine ITSE 106 completion status (note that this MAIS LINC course is now known as PEERRS_CUI_T100)
    query = 'SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk AND b.Code in (\'PEERRS_CUI_T100 \') and d.Username in (\'' + username[1] + '\');'

    mais_cursor.execute(query)
    result = mais_cursor.fetchone()

    if result == None:
        itse106_completed = 0
    else:
        itse106_completed = 1

    # Determine PEERRS_DOJ_BulkData_T100 completion status
    query = 'SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk AND b.Code in (\'PEERRS_DOJ_BulkData_T100\') and d.Username in (\'' + username[1] + '\');'

    mais_cursor.execute(query)
    result = mais_cursor.fetchone()

    if result == None:
        bulkdata_completed = 0
    else:
        bulkdata_completed = 1

    # Print data
    print(f"{username[3]:<{width_lastname}} {username[2]:<{width_firstname}} {username[1]:<{width_uniqname}} {dce101_completed:<{width_dce101}d} {bulkdata_completed:<{width_bulkdata}d} {itse106_completed:<{width_itse106}d}")

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
