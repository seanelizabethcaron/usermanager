#!/usr/bin/python

import os, cgi, time, sys, MySQLdb, ConfigParser, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

cfg = ConfigParser.ConfigParser()
cfg.read('/opt/usermanager/etc/usermanager.ini')

dbuser = cfg.get('database', 'user')
dbpass = cfg.get('database', 'passwd')
dbname = cfg.get('database', 'db')
dbhost = cfg.get('database', 'host')

# Connect to the database
db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

user = sys.argv[1]

print "Marking account approved in DB..."
# Mark the account as approved in the DB
curs = db.cursor()
query = 'UPDATE users SET approved = 1 WHERE uniqname = \'' + user + '\';'

curs.execute(query)
db.commit()

print "Completed."

# Gather some information we will need to send an update to the requester
print "Trying to locate requestor in DB..."
curs = db.cursor()
query = 'SELECT * FROM users WHERE uniqname = \'' + user + '\';'
curs.execute(query)
report = curs.fetchone()
print "Completed."

serialnum = report[0]
firstname = report[3]
lastname = report[4]
requester = report[10]

# Try to fetch this field
approval_reason = '' 

print "Trying to locate requestor e-mail address in DB..."
curs = db.cursor()
query = 'SELECT COUNT(*) FROM users where uniqname = \'' + requester + '\';'
curs.execute(query)
report = curs.fetchone()
countup = report[0]
print "Completed."

if countup == 0:
    print "Assuming e-mail address is requestor@umich.edu"
    requestermail = requester + '@umich.edu'
else:
    print "Finding requestor e-mail address in DB..."
    curs = db.cursor()
    query = 'SELECT emailaddress FROM users where uniqname = \'' + requester + '\';'
    curs.execute(query)
    report = curs.fetchone()
    requestermail = report[0]
    print "Complete."

if approval_reason:
    emailtext = '<html><head></head><body>Dear requester,<br><br>A new user account on the CSG cluster has been <b>approved</b> for ' + firstname + ' ' + lastname + '. The account will be created and an e-mail will be sent to the new user with account information. <br><br>Reviewer notes:<br><br>' + approval_reason + '<br><br>Thank you,<br><br>User Manager Process</body></html>'
else:
    emailtext = '<html><head></head><body>Dear requester,<br><br>A new user account on the CSG cluster has been <b>approved</b> for ' + firstname + ' ' + lastname + '. The account will be created and an e-mail will be sent to the new user with account information. <br><br>Thank you,<br><br>User Manager Process</body></html>'

msg = MIMEMultipart('alternative')

msg['Subject'] = 'CSG cluster account approval notification for ' + firstname + ' ' + lastname
msg['From'] = 'do-not-reply@umich.edu'
msg['To'] = requestermail

part1 = MIMEText(emailtext, 'html')

msg.attach(part1)

print "Attempting to send e-mail..."
s = smtplib.SMTP('localhost')
s.sendmail('do-not-reply@umich.edu', requestermail, msg.as_string())
s.quit()
print "Complete."

