#!/usr/bin/python3

#
# Requires packages: python3-ldap, python3-mysqldb python3-pymssql
#

def generate_html_header():
    print('Content-type: text/html\n')
    print('<!DOCTYPE html>')
    print('<html>')
    print('<head>')
    print('<meta charset="utf-8">')
    print('<title>CSG User Account Request</title>')
    print('<link href="/usermanager/style.css" type="text/css" rel="stylesheet">')
    print('</head>')
    print('<body>')
    print('<div class="header">')
    print('<div class="header_left">')
    print('<img src="/usermanager/logo.png">')
    print('</div>')
    print('<div class="header_right">')
    print('<b>University of Michigan Center for Statistical Genetics</b><br>')
    print('<b>User Account Request Form</b>')
    print('</div>')
    print('</div>')
    print('<div class="errorcontentouter">')
    print('<div class="errorcontentinner">')

def generate_html_footer():
    print('</div>')
    print('</div>')
    print('<div class="footer">')
    print('<button onclick="window.history.back();">Back</button>')
    print('</div>')
    print('</body>')
    print('</html>')

def generate_html_footer_noback():
    print('</div>')
    print('</div>')
    print('</body>')
    print('</html>')

def no_uniqname_found():
    print('No U-M uniqname found for this individual. Please request a U-M uniqname first before proceeding.')

def account_already_exists():
    print('A CSG account already exists for the individual with the specified uniqname.')

def account_in_database():
    print('The requested account is already present in the database. Please contact a systems administrator.')

def account_request_successful(firstname, lastname):
    print('User account request for ' + firstname + ' ' + lastname + ' was successfully submitted for approval.')

def cosign_failure():
    print('Cosign appears to be broken. Please contact a systems administrator.')

def no_uniqname_specified():
    print('No uniqname was specified. Please go back and be sure a uniqname was entered.')

def no_title_specified():
    print('No title was specified. Please go back and be sure a title was entered.')

def no_email_specified():
    print('No contact e-mail address was specified. Please go back and be sure a contact e-mail was entered.')

def no_reason_specified():
    print('No reason was specified. Please go back and be sure a reason for account creation was entered.')

def no_role_specified():
    print('No role was specified. Please go back and be sure a role for the account was entered.')

def no_groups_specified():
    print('No groups were specified. Please go back and be sure groups are entered.')

def no_startdate_specified():
    print('No start date was specified. Please go back and be sure a start date is entered.')

def no_expirydate_specified():
    print('No expiry date was specified. Please go back and be sure an expiry date is entered.')

def no_approver_specified():
    print('No approver was specified. Please go back and be sure an approver is selected.')

def err_uniqname():
    print('Value for uniqname is out of bounds or contains invalid characters. Please go back and check the uniqname field.')

def err_email():
    print('Value for contact e-mail address is out of bounds or contains invalid characters. Please go back and check the contact e-mail address field.')

def err_title():
    print('Value for title is out of bounds or contains invalid characters. Please go back and check the title field.')

def err_startdate():
    print('Value for start date is out of bounds or contains invalid characters. Please go back and check the start date field.')

def err_expirydate():
    print('Value for expiry date is out of bounds or contains invalid characters. Please go back and check the expiry date field.')

def err_reason():
    print('Value for reason is out of bounds or contains invalid characters. Please go back and check the reason field.')

def err_role():
    print('Value for role is out of bounds or contains invalid characters. Please go back and check the role field.')

def err_groups():
    print('Value for groups is out of bounds or contains invalid characters. Please go back and check the groups field.')

def err_approver():
    print('Value for approver is out of bounds or contains invalid characters. Please go back and check the approver field.')

def sanitize(str_to_check):
    permitted = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890.,@/-_ ')

    if set(str_to_check) <= permitted:
        return True
    else:
        return False

def err_invalid_chars():
    print('Field contains invalid characters. Please go back and check fields for invalid characters.')

# Requires packages: python-ldap, python-mysqldb
import sys,os,cgi,time,ldap,MySQLdb,configparser,smtplib,random,pymssql,datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from string import Template

cfg = configparser.ConfigParser()
cfg.read('/opt/usermanager/etc/usermanager.ini')

dbuser = cfg.get('database', 'user')
dbpass = cfg.get('database', 'passwd')
dbname = cfg.get('database', 'db')
dbhost = cfg.get('database', 'host')
audit = cfg.getboolean('logging', 'audit')
debug = cfg.getboolean('logging', 'debug')
audit_log_file = cfg.get('logging', 'auditlog')
debug_log_file = cfg.get('logging', 'debuglog')

mais_dbhost = cfg.get('maislinc', 'mais_dbhost')
mais_dbuser = cfg.get('maislinc', 'mais_dbuser')
mais_passwd = cfg.get('maislinc', 'mais_passwd')
mais_dbport = cfg.get('maislinc', 'mais_dbport')
mais_db = cfg.get('maislinc', 'mais_db')

private_ldap_host = cfg.get('privateldap', 'host')
private_ldap_user_basedn = cfg.get('privateldap', 'user_basedn')
private_ldap_adminuser = cfg.get('privateldap', 'adminuser')
private_ldap_adminpass = cfg.get('privateldap', 'adminpass')

campus_ldap_host = cfg.get('campusldap', 'host')
campus_ldap_basedn = cfg.get('campusldap', 'basedn')

pending_tpl = cfg.get('email', 'pending_tpl')
confirm_tpl = cfg.get('email', 'confirm_tpl')

# Set umask such that both root and www-data can write to logfiles
os.umask(0o011)

if debug:
    debuglog = open(debug_log_file, 'a+')

if audit:
    auditlog = open(audit_log_file, 'a+')

# Get environment variable REMOTE_USER from Cosign to determine requestor uniqname
try:
    requestor = os.environ["REMOTE_USER"]
# If that fails to occur, we will shut down for security.
except KeyError:
    generate_html_header()
    cosign_failure()
    generate_html_footer()
    sys.exit(0)

# Grab all form data and throw up an error message if a field is missing
form = cgi.FieldStorage()

uniqname = form.getvalue('uniqname')
uniqname = uniqname.lower()

if not uniqname:
    generate_html_header()
    no_uniqname_specified()
    generate_html_footer()
    sys.exit(0)

title = form.getvalue('title')
title = title.capitalize()

if not title:
    generate_html_header()
    no_title_specified()
    generate_html_footer()
    sys.exit(0)

email = form.getvalue('email')
email = email.lower()

if not email:
    generate_html_header()
    no_email_specified()
    generate_html_footer()
    sys.exit(0)

reason = form.getvalue('reason')
reason = reason.capitalize()

if not reason:
    generate_html_header()
    no_reason_specified()
    generate_html_footer()
    sys.exit(0)

role = form.getvalue('role')
if not role:
    generate_html_header()
    no_role_specified()
    generate_html_footer()
    sys.exit(0)

groups = form.getvalue('groups')

# In case the groups were specified in caps or mixed case
groups = groups.lower()

if not groups:
    generate_html_header()
    no_groups_specified()
    generate_html_footer()
    sys.exit(0)

startdate = form.getvalue('startdate')
if not startdate:
    generate_html_header()
    no_startdate_specified()
    generate_html_footer()
    sys.exit(0)

expirydate = form.getvalue('expirydate')
if not expirydate:
    generate_html_header()
    no_expirydate_specified()
    generate_html_footer()
    sys.exit(0)

if form.getvalue('topmed_user'):
    topmed_user = 1
else:
    topmed_user = 0

approver = form.getvalue('approver')
if not approver:
    generate_html_header()
    no_approver_specified()
    generate_html_footer()
    sys.exit(0)

# Validate form field lengths
if len(uniqname) > 8 or not sanitize(uniqname):
    generate_html_header()
    err_uniqname()
    generate_html_footer()
    sys.exit(0)

if len(email) > 128 or not sanitize(email):
    generate_html_header()
    err_email()
    generate_html_footer()
    sys.exit(0)

if len(title) > 128 or not sanitize(title):
    generate_html_header()
    err_title()
    generate_html_footer()
    sys.exit(0)

if len(startdate) > 16 or not sanitize(startdate):
    generate_html_header()
    err_startdate()
    generate_html_footer()
    sys.exit(0)

if len(expirydate) > 16 or not sanitize(expirydate):
    generate_html_header()
    err_expirydate()
    generate_html_footer()
    sys.exit(0)

if len(reason) > 255 or not sanitize(reason):
    generate_html_header()
    err_reason()
    generate_html_footer()
    sys.exit(0)

if len(role) > 64 or not sanitize(role):
    generate_html_header()
    err_role()
    generate_html_footer()
    sys.exit(0)

if len(groups) > 1024 or not sanitize(groups):
    generate_html_header()
    err_groups()
    generate_html_footer()
    sys.exit(0)

if len(approver) > 8 or not sanitize(approver):
    generate_html_header()
    err_approver()
    generate_html_footer()
    sys.exit(0)

# Do we want to create a Samba account when we provision the home directory?
create_samba = 0

# Transform the specified role into a home directory and any associated
# additional group memberships
if role == 'alumni_user':
    home_host = 'csgalumni'
    homedir = '/net/csgalumni/home/' + uniqname
elif role == 'boehnke_user':
    # Randomly assign the user a home directory on snowwhite or dumbo
    c = random.randint(1, 2)
    if c == 1:
        home_host = 'dumbo'
        homedir = '/net/dumbo/home/' + uniqname
    elif c == 2:
        home_host = 'snowwhite'
        homedir = '/net/snowwhite/home/' + uniqname
elif role == 'abecasis_user':
    # Randomly assign the user a home directory on wonderland or fantasia
    c = random.randint(1,2)
    if c == 1:
        home_host = 'fantasia'
        homedir = '/net/fantasia/home/' + uniqname
    elif c == 2:
        home_host = 'wonderland'
        homedir = '/net/wonderland/home/' + uniqname
elif role == 'zoellner_user':
    # Randomly assign the user a home directory on wonderland or fantasia
    c = random.randint(1,2)
    if c == 1:
        home_host = 'fantasia'
        homedir = '/net/fantasia/home/' + uniqname
    elif c == 2:
        home_host = 'wonderland'
        homedir = '/net/wonderland/home/' + uniqname
elif role == 'scott_user':
    # Randomly assign the user a home directory on snowwhite or dumbo
    c = random.randint(1, 2)
    if c == 1:
        home_host = 'dumbo'
        homedir = '/net/dumbo/home/' + uniqname
    elif c == 2:
        home_host = 'snowwhite'
        homedir = '/net/snowwhite/home/' + uniqname
elif role == 'willer_user':
    home_host = 'hunt'
    homedir = '/net/hunt/home/' + uniqname
elif role == 'zhou_user':
    home_host = 'mulan'
    homedir = '/net/mulan/home/' + uniqname
elif role == 'external_user':
    home_host = 'sandbox'
    homedir = '/net/sandbox/home/' + uniqname
elif role == 'psoriasis_user':
    home_host = 'psoriasis'
    homedir = '/net/psoriasis/home/' + uniqname
elif role == 'mukherjee_user':
    home_host = 'junglebook'
    homedir = '/net/junglebook/home/' + uniqname
elif role == 'fritsche_user':
    home_host = 'junglebook'
    homedir = '/net/junglebook/home/' + uniqname
elif role == 'kardiasmith_user':
    create_samba = 1
    home_host = 'orion'
    homedir = '/net/orion/home/' + uniqname

if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': Got form data:\n')
    debuglog.write(debug_time + ':     Uniqname = ' + uniqname + '\n')
    debuglog.write(debug_time + ':     Title = ' + title + '\n')
    debuglog.write(debug_time + ':     Email = ' + email + '\n')
    debuglog.write(debug_time + ':     Reason = ' + reason + '\n')
    debuglog.write(debug_time + ':     Role = ' + role + '\n')
    debuglog.write(debug_time + ':     Groups = ' + groups + '\n')
    debuglog.write(debug_time + ':     Homedir = ' + homedir + '\n')
    debuglog.write(debug_time + ':     Startdate = ' + startdate + '\n')
    debuglog.write(debug_time + ':     Expirydate = ' + expirydate + '\n')
    debuglog.write(debug_time + ':     Approver = ' + approver + '\n')
    debuglog.write(debug_time + ':     Requestor = ' + requestor + '\n')
    debuglog.write(debug_time + ': Received HTTP environment variables:\n')
    for name, value in os.environ.items():
        debuglog.write(debug_time + ':     ' + name + ' = ' + value + '\n')
    debuglog.write('\n')

# Do an LDAP query to the CSG LDAP. If the account already exists, generate a notification page for the end user

#l = ldap.open("csgadmin.csgstat.sph.umich.edu")
l = ldap.initialize('ldap://' + private_ldap_host + ':389')
l.protocol_version = ldap.VERSION3
baseDN = private_ldap_user_basedn
searchScope = ldap.SCOPE_SUBTREE
retrieveAttributes = ["uid"]
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

if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': Result set from initial query against CSG LDAP is ' + str(result_set) + '\n')

if (result_set != []):
    generate_html_header()
    account_already_exists()
    generate_html_footer()
    sys.exit(0)

# Do an LDAP query to the ITCS LDAP. If we cannot find the uniqname, generate a notification page for the end user
#  that they need to request a uniqname first.

#l = ldap.open("ldap.itd.umich.edu")
l = ldap.initialize('ldap://' + campus_ldap_host + ':389')
l.protocol_version = ldap.VERSION3
baseDN = campus_ldap_basedn
searchScope = ldap.SCOPE_SUBTREE
retrieveAttributes = ["uidNumber", "displayName", "sn", "givenName", "cn"]
searchFilter = "uid=" + uniqname
ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
res_set = []
while 1:
    result_type, result_data = l.result(ldap_result_id, 0)
    if (result_data == []):
        break
    else:
        if result_type == ldap.RES_SEARCH_ENTRY:
            res_set.append(result_data)

if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': Result set from query against U-M LDAP is ' + str(res_set) + '\n')

if (res_set == []):
    generate_html_header()
    no_uniqname_found()
    generate_html_footer()
    sys.exit(0)

# Extract displayName and uidNumber reported by ITCS LDAP.

dn, results = res_set[0][0]

# Sometimes, users are missing displayName, cn, givenName, sn, or all of the above. Attempt to figure out the
# first name and last name of the user from one or more of these attributes.

displayType = 'USE_DISPLAYNAME'

try:
    displayName = results['displayName'][0]
except KeyError:
    displayType = 'USE_CN'
    try:
        cn = results['cn'][0]
    except KeyError:
        displayType = 'USE_GIVENNAME_SN'

        try:
            givenName = results['givenName'][0]
        except KeyError:
            displayType = 'USE_UNIQNAME'
            givenName = uniqname

        try:
            sn = results['sn'][0]
        except KeyError:
            sn = uniqname

if displayType == 'USE_DISPLAYNAME':
    displayName_segments = displayName.split()
    firstname = displayName_segments[0]
    lastname = displayName_segments[-1]
elif displayType == 'USE_CN':
    cn_segments = cn.split()
    firstname = cn_segments[0]
    lastname = cn_segments[-1]
elif displayType == 'USE_GIVENNAME_SN':
    firstname = givenName
    lastname = sn
else:
    firstname = uniqname
    lastname = uniqname

fistname = firstname.capitalize()
lastname = lastname.capitalize()

uid_number = results['uidNumber'][0]

if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': UID number reported by U-M LDAP is ' + uid_number.decode() + '\n')
    debuglog.write(debug_time + ': First name and last name reported by U-M LDAP is ' + firstname.decode() + ' ' + lastname.decode() + '\n')

# If the account does not exist, add it to the database with approved flag = false
#  Then send an e-mail to the approver, with a link to the Approver dashboard

# Connect to the database
db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

# Check to see that the account isn't already in the database.
curs = db.cursor()
query = 'SELECT COUNT(*) FROM users where uniqname = \'' + uniqname + '\';'
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')

curs.execute(query)
report = curs.fetchone()
countup = report[0]
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': Result count is ' + str(countup) + '\n')

# If it is, throw up an error and stop processing
if countup != 0:
    generate_html_header()
    account_in_database()
    generate_html_footer()
    sys.exit(1)

# Now that we have finished checking database sanity, enter the user account into
#  the database.
curs = db.cursor()
# We will populate this in production by reading a Cosign environment variable
query = 'INSERT INTO users (uniqname,uidnumber,firstname,lastname,emailaddress,title,startdate,enddate,approver,requestor,reason,role,approved,rejected,created,expired,locked,reactivate) VALUES (\'' + uniqname + '\',' + uid_number.decode() + ',\'' + firstname.decode() + '\',\'' + lastname.decode() + '\',\'' + email + '\',\'' + title + '\',\'' + startdate + '\',\'' + expirydate + '\',\'' + approver + '\',\'' + requestor + '\',\'' + reason + '\',\'' + role + '\',0,0,0,0,0,0);'
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')

curs.execute(query)
# We need to have a db.commit() following INSERT statements otherwise the statement may appear to not have executed
db.commit()

# Now determine the unique serial number MySQL assigned for that user account
curs = db.cursor()
query = 'SELECT serialnum FROM users where uniqname = \'' + uniqname + '\';'
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')

curs.execute(query)
report = curs.fetchone()
found_serialnum = report[0]
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': Found serial number ' + str(found_serialnum) + '\n')

# Now add the home directory to the home directory table
curs = db.cursor()
query = 'INSERT INTO homes (serialnum, host, path, created) VALUES (' + str(found_serialnum) + ', \'' + home_host + '\',\'' + homedir + '\', 0);'
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
curs.execute(query)
db.commit()

# Ensure the formatting of the list of groups we received is clean
groups_split = groups.split(',')

groups_list = [ ]

for item in groups_split:
    item = item.strip()
    groups_list.append(item)

groups = ''

for item in groups_list:
    groups = groups + item + ','

groups = groups[:-1]

if groups[0] == ',':
    groups = groups[1:]

# Add the groups to the groups table
curs = db.cursor()
query = 'INSERT INTO groups (serialnum, memberof) VALUES (' + str(found_serialnum) + ', \'' + groups + '\');'
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')

curs.execute(query)
db.commit()

# Gather training modules completion data in MAIS LINC
# user name is in variable uniqname

mais_dbase = pymssql.connect(server=mais_dbhost, user=mais_dbuser, password=mais_passwd, database=mais_db, port=mais_dbport)
mais_cursor = mais_dbase.cursor()

# Determine DCE 101 completion status
query = 'SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk AND b.Code in (\'DCE101\') and d.Username in (\'' + uniqname + '\');'

mais_cursor.execute(query)
result = mais_cursor.fetchone()

if result == None:
    dce101_completed = 0
else:
    dce101_completed = 1

# Determine ITSE 106 completion status (note that this MAIS LINC course is now known as PEERRS_CUI_T100)
query = 'SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk AND b.Code in (\'PEERRS_CUI_T100 \') and d.Username in (\'' + uniqname + '\');'

mais_cursor.execute(query)
result = mais_cursor.fetchone()

if result == None:
    itse106_completed = 0
else:
    itse106_completed = 1

# If the required trainings have already been completed, be sure not to hold the account
if dce101_completed and not topmed_user:
    held_since = '0000-00-00'
    held_pending = 0
    send_reminder = 0
elif dce101_completed and itse106_completed and topmed_user:
    held_since = '0000-00-00'
    held_pending = 0
    send_reminder = 0
# Otherwise hold the account and set reminder trigger data
else:
    held_since = datetime.datetime.now().strftime("%Y-%m-%d")
    held_pending = 1
    send_reminder = 1

# Update trainings table with gathered information
curs = db.cursor()
query = 'INSERT INTO trainings (serialnum, topmed_user, dce101_comp, itse106_comp, held_pending, held_since, send_reminder) VALUES (' + str(found_serialnum) + ', ' + str(topmed_user) + ', ' + str(dce101_completed) + ', ' + str(itse106_completed) + ', ' + str(held_pending) + ', \'' + held_since + '\', ' + str(send_reminder) + ');'
curs.execute(query)
db.commit()

# Add users getting Samba accounts to the samba and smbpasswd_workqueue tables
if create_samba:
    curs = db.cursor()
    query = 'INSERT INTO samba (serialnum, host, uniqname, created, locked) VALUES (' + str(found_serialnum) + ',\'' + home_host + '\',\'' + uniqname + '\',0,0);'
    curs.execute(query)
    db.commit()

    curs = db.cursor()
    query = 'INSERT INTO smbpasswd_workqueue (host, uniqname, action, ready) VALUES (\'' + home_host + '\',\'' + uniqname + '\',\'a\',0);'
    curs.execute(query)
    db.commit()

# Update the audit log
if audit:
    audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    auditlog.write(audit_time + ': Received request to create user account ' + uniqname + ' from ' + requestor + ' with approver ' + approver + '\n')
    auditlog.write(audit_time + ': First name = ' + firstname.decode() + ' Last name = ' + lastname.decode() + '\n')
    auditlog.write(audit_time + ': Contact email = ' + email + '\n')
    auditlog.write(audit_time + ': Title = ' + title + ' Reason = ' + reason + '\n')
    auditlog.write(audit_time + ': Role = ' + role + '\n')
    auditlog.write(audit_time + ': Groups = ' + groups + ' Home directory = ' + homedir + ' Create Samba account = ' + str(create_samba) + '\n')
    auditlog.write(audit_time + ': Start date = ' + startdate + ' Expiry date = ' + expirydate + '\n')
    auditlog.close()

# Send an e-mail to the approver to let them know they have a new pending request
approvermail = approver + '@umich.edu'

with open(pending_tpl) as tp:
    lines = tp.read()

tpl = Template(lines)

emailtext = tpl.substitute(FIRSTNAME=firstname.decode(), LASTNAME=lastname.decode(), REQUESTOR=requestor, STARTDATE=startdate, EXPIRYDATE=expirydate, TITLE=title, ROLE=role, REASON=reason, EMAIL=email, GROUPS=groups, HOMEDIR=homedir)

msg = MIMEMultipart('alternative')

msg['Subject'] = 'New CSG cluster account request pending approval for ' + firstname.decode() + ' ' + lastname.decode()
msg['From'] = 'do-not-reply@umich.edu'
msg['To'] = approvermail

part1 = MIMEText(emailtext, 'html')

msg.attach(part1)

s = smtplib.SMTP('localhost')
s.sendmail('do-not-reply@umich.edu', approvermail, msg.as_string())
s.quit()

# Send an e-mail to the requester so they know their request was received and is in process

# See if we can find the requester in our table of users, so we can dereference their uniqname to an email address on file
#  If so, we will use that email address to contact the requestor with status updates
#  Otherwise we will assume the requester email address is requestor_uniqname@umich.edu

curs = db.cursor()
query = 'SELECT COUNT(*) FROM users where uniqname = \'' + requestor + '\';'
curs.execute(query)
report = curs.fetchone()
countup = report[0]

if countup == 0:
    requestermail = requestor + '@umich.edu'
else:
    curs = db.cursor()
    query = 'SELECT emailaddress FROM users where uniqname = \'' + requestor + '\';'
    curs.execute(query)
    report = curs.fetchone()
    requestermail = report[0]

with open(confirm_tpl) as tp:
    lines = tp.read()

tpl = Template(lines)

emailtext = tpl.substitute(REQUESTOR=requestor, FIRSTNAME=firstname.decode(), LASTNAME=lastname.decode())

msg = MIMEMultipart('alternative')

msg['Subject'] = 'New CSG cluster account request receipt confirmation for ' + firstname.decode() + ' ' + lastname.decode()
msg['From'] = 'do-not-reply@umich.edu'
msg['To'] = requestermail

part1 = MIMEText(emailtext, 'html')

msg.attach(part1)

s = smtplib.SMTP('localhost')
s.sendmail('do-not-reply@umich.edu', requestermail, msg.as_string())
s.quit()

# Generate a page to inform the requestor that the account request was successfully processed
generate_html_header()
account_request_successful(firstname.decode(), lastname.decode())
generate_html_footer_noback()
