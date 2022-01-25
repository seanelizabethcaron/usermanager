#!/usr/bin/python

import sys,os,cgi,time,ldap,MySQLdb, ConfigParser, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

approver = 'scaron'

firstname = 'John'
lastname = 'Smith'

email = 'test@umich.edu'
groups = 'statgen-users,topmed'
home = '/net/fantasia/home'
requestor = 'scaron'
startdate = '2018-01-01'
enddate = '2019-12-31'

# Send an e-mail to the new user with initial account information
approvermail = approver + '@umich.edu'

emailtext = '<html><head></head><body>Dear requestor,<br><br>A new user account on the CSG cluster has been <b>approved</b> for ' + firstname + ' ' + lastname + '.<br><br>Thank you,<br><br>User Manager Process</body></html>'

msg = MIMEMultipart('alternative')

msg['Subject'] = 'New CSG cluster account request pending approval for ' + firstname + ' ' + lastname
msg['From'] = 'do-not-reply@umich.edu'
msg['To'] = approvermail

part1 = MIMEText(emailtext, 'html')

msg.attach(part1)

s = smtplib.SMTP('localhost')
s.sendmail('do-not-reply@umich.edu', approvermail, msg.as_string())
s.quit()

