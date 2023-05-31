#!/usr/bin/python3

#
# Requires packages: python3-ldap, python3-mysqldb
#

import os, cgi,time,ldap,MySQLdb,configparser,smtplib,string,random
import ldap.modlist as modlist
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from string import Template

cfg = configparser.ConfigParser()
cfg.read('/opt/usermanager/etc/usermanager.ini')

dbuser = cfg.get('database', 'user')
dbpass = cfg.get('database', 'passwd')
dbname = cfg.get('database', 'db')
dbhost = cfg.get('database', 'host')

private_ldap_host = cfg.get('privateldap', 'host')
private_ldap_user_basedn = cfg.get('privateldap', 'user_basedn')
private_ldap_group_basedn = cfg.get('privateldap', 'group_basedn')
private_ldap_adminuser = cfg.get('privateldap', 'adminuser')
private_ldap_adminpass = cfg.get('privateldap', 'adminpass')

audit = cfg.getboolean('logging', 'audit')
debug = cfg.getboolean('logging', 'debug')
audit_log_file = cfg.get('logging', 'auditlog')
debug_log_file = cfg.get('logging', 'debuglog')

disabled_tpl = cfg.get('email', 'disabled_tpl')

# Set umask such that both root and www-data can write to logfiles
os.umask(0o011)

if debug:
    debuglog = open(debug_log_file, 'a+')

if audit:
    auditlog = open(audit_log_file, 'a+')

# Connect to the database
db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

# Get the current date in a format consistent with that used in the database to mark expirations
todays_date = time.strftime("%Y-%m-%d", time.localtime())
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': Scan and disable process found the date to be ' + todays_date + '\n')

# Check to see if there are any accounts in the database with a expiry date of today
curs = db.cursor()
query = 'SELECT * FROM users WHERE expired = 0 AND locked = 0 AND enddate = \'' + todays_date + '\';'
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
curs.execute(query)
report = curs.fetchall()

for row in report:
    serialnum = row[0]
    uniqname = row[1]
    uidnumber = row[2]
    firstname = row[3]
    lastname = row[4]
    email = row[5]

    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': Scan and disable found account ' + uniqname + ' should be disabled today\n')

    # Update the database to note the account having expired
    curs = db.cursor()
    query = 'UPDATE users SET expired = 1 where uniqname = \'' + uniqname + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    db.commit()

    l = ldap.initialize('ldap://' + private_ldap_host + ':389')
    # We need to bind otherwise the userPassword attribute will be unavailable
    l.simple_bind_s(private_ldap_adminuser, private_ldap_adminpass)

    l.protocol_version = ldap.VERSION3
    baseDN = private_ldap_user_basedn
    searchScope = ldap.SCOPE_SUBTREE
    retrieveAttributes = ["uid", "userPassword"]
    searchFilter = "uid=" + uniqname
    ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
    result_set = []
    while 1:
        result_type, result_data = l.result(ldap_result_id, 0)
        if (result_data == []):
            break
        else:
            if result_type == ldap.RES_SEARCH_ENTRY:
                result_set.append(result_data)

    dn, results = result_set[0][0]
    display_name = results['uid'][0]
    user_password = results['userPassword'][0]

    # GoSA marks accounts as being locked by putting an exclamation point between the hash type and the hash itself
    locked_pwd = user_password.decode().replace("}", "}!")

    # Write back the updated password to LDAP and lock the account
    modl = [(ldap.MOD_REPLACE, 'userPassword', [locked_pwd.encode()])]
    l.modify_s(dn, modl)

    # Lock the Samba account if applicable
    
    # Determine if the user has a Samba account that is unlocked
    curs = db.cursor()
    query = 'SELECT * FROM samba WHERE uniqname = \' + uniqname + \' AND created = 1 AND locked = 0;'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    report = curs.fetchone()
    
    # If the account exists in the Samba table as created, add a smbpasswd_workqueue entry to disable it
    if report != None:
        # First we need to figure out which host contains the user home directory
        curs = db.cursor()
        query = 'SELECT * FROM homes WHERE serialnum = ' + serialnum + ';'
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
        curs.execute(query)
        report = curs.fetchone()

        home_host = report[1]
    
        curs = db.cursor()
        query = 'INSERT INTO smbpasswd_workqueue (host, uniqname, action, ready) VALUES (\'' + home_host + '\',\'' + uniqname + '\',\'d\',1);'
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
        curs.execute(query)
        db.commit()
        
    # Update the database to note the account having been locked
    curs = db.cursor()
    query = 'UPDATE users SET locked = 1 where uniqname = \'' + uniqname + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    db.commit()

    # Update the audit log
    if audit:
        audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        auditlog.write(audit_time + ': Scan and disable successfully disabled account ' + uniqname + '\n')

    # Send a brief notification e-mail to each user who has their account disabled
    with open(disabled_tpl) as tp:
        lines = tp.read()

    tpl = Template(lines)

    emailtext = tpl.substitute(FIRSTNAME=firstname)
    
    msg = MIMEMultipart('alternative')

    # In production, update this to send to the actual users using their email addresses pulled from the DB
    msg['Subject'] = 'CSG cluster account expiry notification for ' + uniqname 
    msg['From'] = 'do-not-reply@umich.edu'
    msg['To'] = email

    part1 = MIMEText(emailtext, 'html')
    
    msg.attach(part1)
    
    s = smtplib.SMTP('localhost')
    s.sendmail('do-not-reply@umich.edu', email, msg.as_string())
    s.quit()

# Drop any rejected requests from the database so as to clear space for a possible resubmission of the request
curs = db.cursor()
query = 'SELECT * FROM users WHERE rejected = 1;'
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
curs.execute(query)
report = curs.fetchall()

# For each rejected account request, remove it from all tables
for row in report:
    serialnum = row[0]
    uniqname = row[1]

    # Remove from users table
    curs = db.cursor()
    query = 'DELETE FROM users WHERE serialnum = ' + str(serialnum) + ';'
    curs.execute(query)
    db.commit()

    # Remove from groups table
    curs = db.cursor()
    query = 'DELETE from groups WHERE serialnum = ' + str(serialnum) + ';'
    curs.execute(query)
    db.commit()

    # Remove from homes table
    curs = db.cursor()
    query = 'DELETE FROM homes WHERE serialnum = ' + str(serialnum) + ';'
    curs.execute(query)
    db.commit()

    # Update audit log
    if audit:
        audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        auditlog.write(audit_time + ': Scan and disable purging denied account request for ' + uniqname + '\n')

# Close audit log
if audit:
    auditlog.close()

# Close debug log
if debug:
    debuglog.close()
