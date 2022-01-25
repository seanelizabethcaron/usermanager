#!/usr/bin/python

import sys,os,cgi,time,ldap,MySQLdb, ConfigParser, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Added for template
from string import Template

approver = 'scaron'

firstname = 'John'
lastname = 'Smith'

uniqname = 'jsmith'
randomPassword = 'PASSWORD'

email = 'test@umich.edu'
groups = 'statgen-users,topmed'
home = '/net/fantasia/home'
requestor = 'scaron'
startdate = '2018-01-01'
enddate = '2019-12-31'

# Send an e-mail to the new user with initial account information
approvermail = approver + '@umich.edu'

# Added for template
with open('newuser.tpl') as tp:
    lines = tp.read()

print(lines)
tpl = Template(lines)

emailtext = ""

emailtext = tpl.substitute(FIRSTNAME=firstname, RANDOMPASSWORD=randomPassword, UNIQNAME=uniqname)

print(emailtext)

msg = MIMEMultipart('alternative')

msg['Subject'] = 'New CSG cluster account request receipt confirmation for ' + firstname + ' ' + lastname
msg['From'] = 'do-not-reply@umich.edu'
msg['To'] = approvermail

part1 = MIMEText(emailtext, 'html')

msg.attach(part1)

s = smtplib.SMTP('localhost')
s.sendmail('do-not-reply@umich.edu', approvermail, msg.as_string())
s.quit()

