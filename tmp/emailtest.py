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
title = 'Systems Administrator Sr'
role = 'user'
reason = 'Just testing'

# Send an e-mail to the new user with initial account information
approvermail = approver + '@umich.edu'

emailtext = '<html><head></head><body>Dear approver,<br><br>A new user account on the CSG cluster has been requested for ' + firstname + ' ' + lastname + ' by ' + requestor + '. Please visit the <a href="https://csgadmin.sph.umich.edu/cgi-bin/usermanager/approver_dashboard.py">approver dashboard</a> to review the request.<br><br>Detailed request information:<br><br>Start date: <div style="font: normal 10pt \'Courier\';">' + startdate + '</div><br>End date: <div style="font: normal 10pt \'Courier\';">' + enddate + '</div><br>Title: <div style="font: normal 10pt \'Courier\';">' + title + '</div><br>Role: <div style="font: normal 10pt \'Courier\';">' + role + '</div><br>Reason: <div style="font: normal 10pt \'Courier\';">' + reason + '</div><br>Contact e-mail: <div style="font: normal 10pt \'Courier\';">' + email + '</div><br>Groups: <div style="font: normal 10pt \'Courier\';">' + groups + '</div><br>Home: <div style="font: normal 10pt \'Courier\';">' + home + '</div><br>Thank you,<br><br>User Manager Process</body></html>'

msg = MIMEMultipart('alternative')

msg['Subject'] = 'New CSG cluster account request pending approval for ' + firstname + ' ' + lastname
msg['From'] = 'do-not-reply@umich.edu'
msg['To'] = approvermail

part1 = MIMEText(emailtext, 'html')

msg.attach(part1)

s = smtplib.SMTP('localhost')
s.sendmail('do-not-reply@umich.edu', approvermail, msg.as_string())
s.quit()

