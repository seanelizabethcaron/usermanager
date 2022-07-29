#!/usr/bin/python3

#
# Requires packages: python3-mysqldb python3-ldap
#

import os, cgi, time, sys, MySQLdb, configparser, smtplib, json, requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
try:
    import urllib.parse
except ImportError:
    import urlparse

from apidirectory import ApiDirectory

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

approvers = cfg.get('approvers', 'approvers')

clientid = cfg.get('mcommunity', 'clientid')
clientsecret = cfg.get('mcommunity', 'clientsecret')

approved_tpl = cfg.get('email', 'approved_tpl')
denied_tpl = cfg.get('email', 'denied_tpl')

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
    print('<b>User Account Manager Approver Dashboard</b>')
    print('</div>')
    print('</div>')
    print('<div class="approvercontentouter">')
    print('<div class="approvercontentinner">')

def generate_html_footer():
    print('</div>')
    print('</div>')
    print('</body>')
    print('</html>')

def cosign_failure():
    print('Cosign appears to be broken. Please contact a systems administrator.')

def approved_and_rejected():
    print('A request was checked both approved and rejected. Please go back and try again.')

def not_an_approver():
    print('Your account has not been configured for the request approval role. Please contact a systems administrator.')

class IamGroupUpdate:
    client_id = clientid
    secret = clientsecret
    scope = "iamgroups"
    token_url = "https://apigw.it.umich.edu/um/inst/oauth2/token"
    url_base = "https://apigw.it.umich.edu/um/iamGroups"

    groupName = "csg-it-announcements"
    groupDn = "cn={},ou=user groups,ou=groups,dc=umich,dc=edu".format(groupName)

    # This will update the group with the supplied values. Note that the behavior of MCommunity on a simple
    # add is to wipe and replace the group membership with the argument of the simple add, so we need to
    # dump existing group membership, append our new member and then submit the entire list of users as an
    # update.
    def update_group(self, eMailAddress):

        eMailUser,eMailHost = eMailAddress.split("@")

        # Internal U-M users
        if "umich.edu" in eMailHost:
            url = "members/" + self.groupDn
            existingMembers = self.get_membership(url)

            stringToAppend = 'uid=' + eMailUser + ',ou=people,dc=umich,dc=edu'
            existingMembers.append(stringToAppend)

            data = {'dn': self.groupDn, 'memberDn': existingMembers}
            self.apply_update(data, "update/member")

        # External non-UM users
        else:
            url = "members/" + self.groupDn
            existingExtMembers =  self.get_external_membership(url)

            newExtMembers = [ ]

            for emailAddress in existingExtMembers:
                newExtMembers.append({'email': emailAddress})

            newExtMembers.append({'email': eMailAddress})

            data = {'dn': self.groupDn, 'memberExternal': newExtMembers}
            self.apply_update(data, "update/externalMember")

    def apply_update(self, data, url_endpoint):
        api = ApiDirectory(self.client_id, self.secret, self.scope, self.token_url)
        url = IamGroupUpdate.url_base + '/' + url_endpoint
        response = requests.post(
            url=url,
            data=json.dumps(data),
            headers=api.build_headers(),
            timeout=10
        )

        if (response.status_code != requests.codes.ok):
            print('Response: {}'.format(response))
            print('JSON: {}'.format(response.json()))
            raise Exception("issue with update")

        map = response.json()
        return map

    def get_membership(self, url_endpoint):
        api = ApiDirectory(self.client_id, self.secret, self.scope, self.token_url)
        url = IamGroupUpdate.url_base + '/' + url_endpoint
        response = requests.get(
            url=url,
            headers=api.build_headers(),
            timeout=10
        )

        map = response.json()

        return map["group"]["memberDn"]

    def get_external_membership(self, url_endpoint):
        api = ApiDirectory(self.client_id, self.secret, self.scope, self.token_url)
        url = IamGroupUpdate.url_base + '/' + url_endpoint
        response = requests.get(
            url=url,
            headers=api.build_headers(),
            timeout=10
        )

        map = response.json()

        return map["group"]["memberExternalRaw"]

# Convert comma-delimited string list of approvers to a Python list
approvers_list = approvers.split(",")

# Set umask such that both root and www-data can write to logfiles
os.umask(0o011)

if debug:
    debuglog = open(debug_log_file, 'a+')

if audit:
    auditlog = open(audit_log_file, 'a+')

# Get form data
form = cgi.FieldStorage()
users_to_approve = form.getvalue('approveuser')
users_to_reject = form.getvalue('rejectuser')

# Get environment variable REMOTE_USER from Cosign to determine approver uniqname
try:
    approver = os.environ["REMOTE_USER"]
# If that fails to occur, we will shut down for security.
except KeyError:
    generate_html_header()
    cosign_failure()
    generate_html_footer()
    sys.exit(0)

# Determine if the user that just logged in is an authorized approver
user_is_authorized = False

for user in approvers_list:
    if user == approver:
        user_is_authorized = True
    
# Connect to the database
db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

if users_to_approve or users_to_reject:
    generate_html_header()

    # Catch if someone accidentally checked both the approve and reject boxes for an account request
    if users_to_approve and users_to_reject:
        if type(users_to_approve) is not list:
            users_to_approve = [users_to_approve]

        if type(users_to_reject) is not list:
            users_to_reject = [users_to_reject]

        if set(users_to_approve) & set(users_to_reject):
            approved_and_rejected()
            generate_html_footer()
            sys.exit(0)

    print('<table>')
 
    if users_to_approve:
        #print('<h1>Users to approve:</h1>')

        if type(users_to_approve) is not list:
            users_to_approve = [users_to_approve]

        for user in users_to_approve:
            print('<tr><td><b>Approved</b></td><td>account request for user ' + user + '</td></tr>')

            # Mark the account as approved in the DB
            curs = db.cursor()
            query = 'UPDATE users SET approved = 1 WHERE uniqname = \'' + user + '\';'
            if debug:
                debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                debuglog.write(debug_time + ': SQL query for approved user account ' + user + ' is ' + query + '\n')
            if audit:
                audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                auditlog.write(audit_time + ': Account for ' + user + ' approved by ' + approver + '\n')
            curs.execute(query)
            db.commit()

            # Send an update to the requester to let them know that the account was approved

            # Gather some information we will need to send an update to the requester
            curs = db.cursor()
            query = 'SELECT * FROM users WHERE uniqname = \'' + user + '\';'
            curs.execute(query)
            report = curs.fetchone()

            serialnum = report[0]
            firstname = report[3]
            lastname = report[4]
            usermail = report[5]
            requester = report[10]

            # See if we have some reason text for this user
            user_reasontext_field = 'reasontext_' + user

            # Try to fetch this field
            approval_reason = form.getvalue(user_reasontext_field)

            # Compose and send the notification to the requester

            # See if we can find the requester in our table of users, so we can dereference their uniqname to an email address on file
            #  If so, we will use that email address to contact the requestor with status updates
            #  Otherwise we will assume the requester email address is requestor_uniqname@umich.edu
            curs = db.cursor()
            query = 'SELECT COUNT(*) FROM users where uniqname = \'' + requester + '\';'
            curs.execute(query)
            report = curs.fetchone()
            countup = report[0]

            if countup == 0:
                requestermail = requester + '@umich.edu'
            else:
                curs = db.cursor()
                query = 'SELECT emailaddress FROM users where uniqname = \'' + requester + '\';'
                curs.execute(query)
                report = curs.fetchone()
                requestermail = report[0]

            if not approval_reason:
                approval_reason = "none"

            with open(approved_tpl) as tp:
                lines = tp.read()

            tpl = Template(lines)

            emailtext = tpl.substitute(FIRSTNAME=firstname,LASTNAME=lastname,APPROVAL_REASON=approval_reason)

            msg = MIMEMultipart('alternative')

            msg['Subject'] = 'CSG cluster account approval notification for ' + firstname + ' ' + lastname
            msg['From'] = 'do-not-reply@umich.edu'
            msg['To'] = requestermail

            part1 = MIMEText(emailtext, 'html')

            msg.attach(part1)

            s = smtplib.SMTP('localhost')
            s.sendmail('do-not-reply@umich.edu', requestermail, msg.as_string())
            s.quit()

            # Add the user to our csg-it-announcements email list
            g = IamGroupUpdate()
            g.update_group(usermail)

    if users_to_reject:
        #print('<h1>Users to reject:</h1>')

        if type(users_to_reject) is not list:
            users_to_reject = [users_to_reject]

        for user in users_to_reject:
            print('<tr><td><b>Rejected</b></td><td>account request for user ' + user + '</td></tr>')
            curs = db.cursor()
            query = 'UPDATE users SET rejected = 1 WHERE uniqname = \'' + user + '\';'
            if debug:
                debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                debuglog.write(debug_time + ': SQL query for rejected user account ' + user + ' is ' + query + '\n')
            if audit:
                audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                auditlog.write(audit_time + ': Account for ' + user + ' rejected by ' + approver + '\n')
            curs.execute(query)
            db.commit()

            # Send an update to the requester to let them know that the account was rejected

            # Gather some information we will need to send an update to the requester
            curs = db.cursor()
            query = 'SELECT * FROM users WHERE uniqname = \'' + user + '\';'
            curs.execute(query)
            report = curs.fetchone()

            serialnum = report[0]
            firstname = report[3]
            lastname = report[4]
            requester = report[10]

            # See if we have some reason text for this user
            user_reasontext_field = 'reasontext_' + user

            # Try to fetch this field
            denial_reason = form.getvalue(user_reasontext_field)

            # Compose and send the notification to the requester

            # See if we can find the requester in our table of users, so we can dereference their uniqname to an email address on file
            #  If so, we will use that email address to contact the requestor with status updates
            #  Otherwise we will assume the requester email address is requestor_uniqname@umich.edu
            curs = db.cursor()
            query = 'SELECT COUNT(*) FROM users where uniqname = \'' + requester + '\';'
            curs.execute(query)
            report = curs.fetchone()
            countup = report[0]

            if countup == 0:
                requestermail = requester + '@umich.edu'
            else:
                curs = db.cursor()
                query = 'SELECT emailaddress FROM users where uniqname = \'' + requester + '\';'
                curs.execute(query)
                report = curs.fetchone()
                requestermail = report[0]

            if not denial_reason:
                denial_reason = "none"

            with open(denied_tpl) as tp:
                lines = tp.read()

            tpl = Template(lines)

            emailtext = tpl.substitute(FIRSTNAME=firstname, LASTNAME=lastname, DENIAL_REASON=denial_reason) 

            msg = MIMEMultipart('alternative')

            msg['Subject'] = 'CSG cluster account denial notification for ' + firstname + ' ' + lastname
            msg['From'] = 'do-not-reply@umich.edu'
            msg['To'] = requestermail

            part1 = MIMEText(emailtext, 'html')

            msg.attach(part1)

            s = smtplib.SMTP('localhost')
            s.sendmail('do-not-reply@umich.edu', requestermail, msg.as_string())
            s.quit()

    print('</table>')
    generate_html_footer()

else:
    generate_html_header()

    # If user is not authorized as an approver, print an error message and exit
    if not user_is_authorized:
        not_an_approver()
        generate_html_footer()
        sys.exit(0)

    curs = db.cursor()
    query = 'SELECT COUNT(*) FROM users where approved = 0 and created = 0 and rejected = 0 and approver = \'' + approver + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query to fetch number of accounts pending approval is ' + query + '\n') 
    curs.execute(query)
    report = curs.fetchone()
    countup = report[0]

    if countup > 0:
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': Found ' + str(countup) + ' account requests awaiting approval or rejection\n')
        print('<table>')
        print('<form action="/cgi-bin/usermanager/approver_dashboard.py" method="POST">')
        print('<tr><th>First name</th><th>Last name</th><th>Uniqname</th><th>Groups</th><th>Home</th><th>Start date</th><th>End date</th><th>Requested by</th><th>Approve request</th><th>Deny request</th><th>Reason for decision</th></tr>')

        curs = db.cursor()
        query = 'SELECT * from users where approved = 0 and created = 0 and rejected = 0 and approver = \'' + approver + '\';'
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': SQL query to locate accounts pending review is ' + query + '\n')
        curs.execute(query)
        pending = curs.fetchall()

        toggle = 0

        for pending_u in pending:
            if toggle == 0:
                print('<tr bgcolor=#e6ffe6><td>')
            else:
                print('<tr><td>')

            serialnum = pending_u[0]
            firstname = pending_u[3]
            lastname = pending_u[4]
            uniqname = pending_u[1]
            email = pending_u[5]
            startdate = pending_u[7]
            enddate = pending_u[8]
            requester = pending_u[10]

            # Gather some extra data points in preparation for expanding the approver dashboard to present
            # this information to approvers.

            # Determine which groups were requested for this user account
            curs = db.cursor()
            query = 'SELECT * from groups where serialnum = ' + str(serialnum) + ';'
            curs.execute(query)
            groups = curs.fetchone()

            # Determine which node the home directory was requested on for this accout
            curs = db.cursor()
            query = 'SELECT * from homes where serialnum = ' + str(serialnum) + ';'
            curs.execute(query)
            home = curs.fetchone()

            groups = groups[1]
            home = home[1]

            groups = groups.replace(",", "<br>")

            if debug:
                debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                debuglog.write(debug_time + ': Account pending review with Uniqname = ' + uniqname + ' First name = ' + firstname + ' Last name = ' + lastname + ' Start date = ' + startdate + 'End date = ' + enddate + '\n')

            print(firstname)
            print('</td><td>')
            print(lastname)
            print('</td><td>')
            print(uniqname)
            print('</td><td>')
            print(groups)
            print('</td><td>')
            print(home)
            print('</td><td>')
            print(startdate)
            print('</td><td>')
            print(enddate)
            print('</td><td>')
            print(requester)
            print('</td><td align=center>')
            print('<input type="checkbox" name="approveuser" value="' + uniqname + '">')
            print('</td><td align=center>')
            print('<input type="checkbox" name="rejectuser" value="' + uniqname + '">')
            print('</td><td>')
            print('<input type="text" name="reasontext_' + uniqname + '">')
            print('</td></tr>')

            toggle = not toggle

        print('</table>')
        print('</div>')
        print('</div>')
        print('<div class="footer">')
        print('<button type="submit" name="approveusers">Update approval status for selected users</button>')
        print('</div>')
        print('</body>')
        print('</html>')

    else:
        print('No new account requests awaiting review.')
        generate_html_footer()

db.close()
