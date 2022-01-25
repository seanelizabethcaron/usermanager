#!/usr/bin/python

import sys,os,cgi,time,ldap,MySQLdb, ConfigParser, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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


emailtext = '<html><head></head><body>Hi ' + firstname + ',<br><br>We\'ve set you up with an account on the CSG cluster with the following parameters:<br><br>User name: <tt>' + uniqname + '</tt><br>Password: <tt>' + randomPassword + '</tt><br><br>First thing you receive this message, please take a moment to visit the URL:<br><br>https://csgadmin.sph.umich.edu/gosa<br><br>Sign in with your username and temporary password above, then click the Change password button in the upper right hand corner of the page to reset your cluster password to something of your choice that meets our complexity guidelines.<br><br>Second, please take 30-60 minutes to sign on to MAIS LINC and complete the <A HREF="https://maislinc.umich.edu/maislinc/app/management/LMS_ActDetails.aspx?ActivityId=877">DCE 101: Access and Compliance: Handling Sensitive Institutional Data at U-M</A> e-learning module and attestation.<br><br>Finally, if you are working on the TOPMED project, please also complete the MAIS LINC <A HREF="https://maislinc.umich.edu/mais/html/ITSE106_SecurityControlsCUI.html">Securing Controlled Unclassified Information</A> module.<br><br>Once you\'ve done that, you can log into any of our four general-purpose gateway nodes using your favorite SSH client:<br><br><tt>snowwhite.sph.umich.edu</tt><br><tt>dumbo.sph.umich.edu</tt><br><tt>fantasia.sph.umich.edu</tt><br><tt>wonderland.sph.umich.edu</tt><br><br>Just let us know if any trouble.<br><br>Best,<br><br>CSG Account Administrators</body></html>'

msg = MIMEMultipart('alternative')

msg['Subject'] = 'New CSG cluster account request receipt confirmation for ' + firstname + ' ' + lastname
msg['From'] = 'do-not-reply@umich.edu'
msg['To'] = approvermail

part1 = MIMEText(emailtext, 'html')

msg.attach(part1)

s = smtplib.SMTP('localhost')
s.sendmail('do-not-reply@umich.edu', approvermail, msg.as_string())
s.quit()

