#!/usr/bin/python

import csv, ldap, ConfigParser, MySQLdb, time, sys, os, smtplib,pymssql

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
query = 'SELECT uniqname,firstname,lastname,emailaddress FROM users WHERE approved = 1 AND locked = 0 AND expired = 0 and emailaddress like \'%umich.edu%\';'
local_curs.execute(query)
report = local_curs.fetchall()

# Connect to the MAIS LINC database
mais_db = pymssql.connect(server=mais_dbhost, user=mais_dbuser, password=mais_passwd, database=mais_db, port=mais_dbport)
mais_cursor = mais_db.cursor()

for uniqname in report:
    query = 'SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk AND b.Code in (\'DCE101\') and d.Username in (\'' + uniqname[0] + '\');'

    mais_cursor.execute(query)
    result = mais_cursor.fetchone()

    # DCE101 not completed, send email reminder
    if result == None:
        print 'Sending DCE101 completion reminder for user ' + uniqname[0] + ' to ' + uniqname[3] 

        emailtext = '<html><head></head><body>Dear ' + uniqname[0] + ',<br><br>A review of our records shows that you have an active account on the U-M CSG cluster but have not yet completed the DCE101 IT security awareness training module on MAIS LINC.<br><br>Ensuring that all users on the cluster have completed this training module is an important part of our security compliance obligations to project sponsors that their data is being handled appropriately.<br><br>Please take 30-60 minutes to sign into MAIS LINC and complete the <A HREF="https://maislinc.umich.edu/maislinc/app/management/LMS_ActDetails.aspx?UserMode=0&ActivityId=47169">DCE 101: U-M Data Protection and Responsible Use</A> module. Once you have completed the module, an automated process will update our records and no further action will be required on your part.<br><br>Please contact the CSG IT help desk at <a href="mailto:csg.help@umich.edu">csg.help@umich.edu</a> if you have any questions.<br><br>Thank you,<br><br>CSG Systems Administration Staff</body></html>'

        msg = MIMEMultipart('alternative')

        msg['Subject'] = 'DCE101 MAIS LINC module completion reminder for ' + uniqname[0]
        msg['From'] = 'do-not-reply@umich.edu'
        msg['To'] = uniqname[3]

        part1 = MIMEText(emailtext, 'html')

        msg.attach(part1)

        s = smtplib.SMTP('localhost')
        s.sendmail('do-not-reply@umich.edu', uniqname[3], msg.as_string())
        s.quit()

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

