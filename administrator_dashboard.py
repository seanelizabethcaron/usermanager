#!/usr/bin/python3

#
# Requires packages: python3-mysqldb python3-ldap
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
    print('<b>User Account Manager Systems Administrator Dashboard</b>')
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
    
import os, cgi, time, datetime, sys, MySQLdb, configparser, ldap
import ldap.modlist as modlist

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

# Set umask such that both root and www-data can write to logfiles
os.umask(0o011)

if debug:
    debuglog = open(debug_log_file, 'a+')

if audit:
    auditlog = open(audit_log_file, 'a+')

# Get form data
form = cgi.FieldStorage()

fm_selectuser = form.getvalue('selectuser')
fm_togglelock = form.getvalue('togglelock')
if not fm_togglelock:
    fm_togglelock = False
else:
    fm_togglelock = True

# Get environment variable REMOTE_USER from Cosign to determine approver uniqname
try:
    approver = os.environ["REMOTE_USER"]
# If that fails to occur, we will shut down for security.
except KeyError:
    generate_html_header()
    cosign_failure()
    generate_html_footer()
    sys.exit(0)

# Connect to the database
db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

if fm_selectuser:
    fm_email = form.getvalue('email_' + fm_selectuser)
    fm_enddate = form.getvalue('enddate_' + fm_selectuser)
    if not fm_enddate:
        fm_enddate = ''
    fm_groups = form.getvalue('groups_' + fm_selectuser)

    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': Administrator dashboard got form data:\n')
        debuglog.write(debug_time + ':     Selectuser = ' + str(fm_selectuser) + '\n')
        debuglog.write(debug_time + ':     Togglelock = ' + str(fm_togglelock) + '\n')
        debuglog.write(debug_time + ':     Email = ' + str(fm_email) + '\n')
        debuglog.write(debug_time + ':     Enddate = ' + str(fm_enddate) + '\n')
        debuglog.write(debug_time + ':     Groups = ' + str(fm_groups) + '\n')

    generate_html_header()

    print('<table>')

    # Clean up and listify the groups we received from the form
    fm_groups_split = fm_groups.split(',')

    fm_groups_list = [ ]

    for item in fm_groups_split:
        item = item.strip()
        fm_groups_list.append(item)

    fm_groups = ''

    for item in fm_groups_list:
        fm_groups = fm_groups + item + ','

    fm_groups = fm_groups[:-1]

    curs = db.cursor()
    query = 'SELECT * from users where uniqname = \'' + fm_selectuser + '\';'
    curs.execute(query)
    user = curs.fetchone()

    serialnum = user[0]
    email = user[5]
    enddate = user[8]
    locked_or_unlocked = user[17]

    curs = db.cursor()
    query = 'SELECT * from groups where serialnum = ' + str(serialnum) + ';'
    curs.execute(query)
    groups = curs.fetchone()
    groups = groups[1]

    # Listify and ensure formatting is clean for the groups we fetched
    groups_split = groups.split(',')

    groups_list = [ ]

    for item in groups_split:
        item = item.strip()
        groups_list.append(item)

    groups = ''

    for item in groups_list:
        groups = groups + item + ','

    groups = groups[:-1]

    # At this point we have cleaned group list strings: groups and fm_groups
    # And Python list objects: groups_list and fm_groups_list

    # If toggle lock was selected, toggle the lock state on the account
    if fm_togglelock:
        # Lock account that was previously unlocked
        if locked_or_unlocked == 0:
            todays_date = time.strftime("%Y-%m-%d", time.localtime())

            # Update the expiry date to be the current date for account we are locking
            curs = db.cursor()
            query = 'UPDATE users set enddate = \'' + todays_date + '\' where uniqname = \'' + fm_selectuser + '\';'
            curs.execute(query)
            db.commit()

            # Update the database to note the account having expired
            curs = db.cursor()
            query = 'UPDATE users SET expired = 1 where uniqname = \'' + fm_selectuser + '\';'
            curs.execute(query)
            db.commit()

            l = ldap.initialize('ldap://' + private_ldap_host + ':389')
            # We need to bind otherwise the userPassword attribute will be unavailable
            l.simple_bind_s(private_ldap_adminuser, private_ldap_adminpass)

            l.protocol_version = ldap.VERSION3
            baseDN = private_ldap_user_basedn
            searchScope = ldap.SCOPE_SUBTREE
            retrieveAttributes = ["uid", "userPassword"]
            searchFilter = "uid=" + fm_selectuser
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

            # Update the database to note the account having been locked and make sure the reactivate flag is cleared
            curs = db.cursor()
            query = 'UPDATE users SET locked = 1, reactivate = 0 where uniqname = \'' + fm_selectuser + '\';'
            curs.execute(query)
            db.commit()

            print('<tr><td><b>Locked</b></td><td>account for user ' + fm_selectuser + '</td></tr>')

        # Unlock account that was previously locked
        else:
            # Carve up enddate into component year, month and day
            #   Do we want to take enddate and add a year to that, or todays_date and add a year to that?
            end_yr, end_mo, end_dy = enddate.split('-')

            # Create a datetime object out of old expiry date so we can do some date math on it
            oldexpdate = datetime.datetime(int(end_yr), int(end_mo), int(end_dy))

            # Add a year to the old expiry date when we reactivate accounts
            newexpdate = oldexpdate + datetime.timedelta(days=365)
            newexptuple = newexpdate.timetuple()
            newexpdatestring = time.strftime("%Y-%m-%d", newexptuple)
 
            # Bind to LDAP
            l = ldap.initialize('ldap://' + private_ldap_host + ':389/')
            l.simple_bind_s(private_ldap_adminuser, private_ldap_adminpass)

            l.protocol_version = ldap.VERSION3
            baseDN = private_ldap_user_basedn
            searchScope = ldap.SCOPE_SUBTREE
            retrieveAttributes = ["uid", "userPassword"]
            searchFilter = "uid=" + fm_selectuser
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
            unlocked_pwd = user_password.replace("}!", "}")

            # Write back the updated password to LDAP to unlock the account
            modl = [(ldap.MOD_REPLACE, 'userPassword', [unlocked_pwd])]
            l.modify_s(dn, modl)

            # Unbind from the LDAP directory
            l.unbind_s()

            # Make sure the expired, locked and reactivate flags are cleared
            curs = db.cursor()
            query = 'UPDATE users SET expired = 0, locked = 0, reactivate = 0 where uniqname = \'' + fm_selectuser + '\';'
            curs.execute(query)
            db.commit()

            # Update the expiry date to be the old expiry date plus a year for account we are locking
            curs = db.cursor()
            query = 'UPDATE users set enddate = \'' + newexpdatestring + '\' where uniqname = \'' + fm_selectuser + '\';'
            curs.execute(query)
            db.commit()

            print('<tr><td><b>Unlocked</b></td><td>account for user ' + fm_selectuser + '</td></tr>')

    # If email field was changed, update the database
    if fm_email != email:
        curs = db.cursor()
        query = 'UPDATE users SET emailaddress = \'' + fm_email + '\' where uniqname = \'' + fm_selectuser + '\';'
        curs.execute(query)
        db.commit()

        print('<tr><td><b>Updated</b></td><td>contact e-mail for user ' + fm_selectuser + ' to ' + fm_email + '</td></tr>')

    # If enddate was changed, update the database
    if fm_enddate != enddate:
        curs = db.cursor()
        query = 'UPDATE users SET enddate = \'' + fm_enddate + '\' where uniqname = \'' + fm_selectuser + '\';'
        curs.execute(query)
        db.commit()

        print('<tr><td><b>Updated</b></td><td>expiry date for user ' + fm_selectuser + ' to ' + fm_enddate + '</td></tr>')

    # If list of groups was changed, update the database
    if fm_groups != groups:

        # Bind to LDAP
        l = ldap.initialize('ldap://' + private_ldap_host + ':389/')
        l.simple_bind_s(private_ldap_adminuser, private_ldap_adminpass)

        # Update group membership additions
        for new_group in fm_groups_list:
            if new_group not in groups_list:
                # Set up LDAP search parameters
                baseDN = private_ldap_group_basedn
                searchScope = ldap.SCOPE_SUBTREE
                retrieveAttributes = ["cn"]
                modl = [(ldap.MOD_ADD, 'memberUid', [fm_selectuser])]

                # For each group, check that it exists in LDAP before we attempt to add a user to it
                searchFilter = "cn=" + new_group
                ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
                result_set = []

                while 1:
                    result_type, result_data = l.result(ldap_result_id, 0)
                    if (result_data == []):
                        break
                    else:
                        if result_type == ldap.RES_SEARCH_ENTRY:
                            result_set.append(result_data)

                # Group exists, go ahead and proceed with the update
                if result_set != []:
                    if audit:
                        audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                        auditlog.write(audit_time + ': Adding ' + fm_selectuser + ' to group ' + new_group + '\n')

                    l.modify_s('cn=' + new_group + ',' + private_ldap_group_basedn, modl)

                    print('<tr><td><b>Added</b></td><td>group membership for user ' + fm_selectuser + ' in ' + new_group + '</td></tr>')

        # Update group membership removals
        for old_group in groups_list:
            if old_group not in fm_groups_list:
                # Set up LDAP search parameters
                baseDN = private_ldap_group_basedn
                searchScope = ldap.SCOPE_SUBTREE
                retrieveAttributes = ["cn"]
                modl = [(ldap.MOD_DELETE, 'memberUid', [fm_selectuser])]

                # For each group, check that it exists in LDAP before we attempt to remove a user from it
                searchFilter = "cn=" + old_group
                ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
                result_set = []
            
                while 1:
                    result_type, result_data = l.result(ldap_result_id, 0)
                    if (result_data == []):
                        break
                    else:
                        if result_type == ldap.RES_SEARCH_ENTRY:
                            result_set.append(result_data)
        
                # Group exists, go ahead and proceed with the update
                if result_set != []:
                    if audit:
                        audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                        auditlog.write(audit_time + ': Removing ' + fm_selectuser + ' from group ' + old_group + '\n')

                    l.modify_s('cn=' + old_group + ',' + private_ldap_group_basedn, modl)

                    print('<tr><td><b>Removed</b></td><td>group membership for user ' + fm_selectuser + ' in ' + old_group + '</td></tr>')

        # Unbind from the LDAP directory
        l.unbind_s()

        # Update database
        curs = db.cursor()
        query = 'UPDATE groups SET memberof = \'' + fm_groups + '\' WHERE serialnum = ' + str(serialnum) + ';'
        curs.execute(query)
        db.commit()

    print('</table>')
    generate_html_footer()

else:
    generate_html_header()

    print('<table>')
    print('<form action="/cgi-bin/usermanager/administrator_dashboard.py" method="POST">')
    print('<tr><th>Select</th><th>Toggle lock</th><th>First name</th><th>Last name</th><th>Uniqname</th><th>Contact e-mail</th><th>Expiry date</th><th>Groups</th></tr>')

    admins = ['scaron', 'sdushett']

    curs = db.cursor()
    if approver in admins:
        query = 'SELECT * from users where created = 1;'
    else:
        query = 'SELECT * from users where approver = \'' + approver + '\' and created = 1;'
    curs.execute(query)
    users = curs.fetchall()

    todays_date = time.strftime("%Y-%m-%d", time.localtime())

    toggle = 0

    for user in users:
        serial = user[0]
        firstname = user[3]
        lastname = user[4]
        uniqname = user[1]
        email = user[5]
        startdate = user[7]
        enddate = user[8]
        locked_or_unlocked = user[17]
        reactivate = user[18]

        curs = db.cursor()
        query = 'SELECT * from groups where serialnum = ' + str(serial) + ';'
        curs.execute(query)
        groups = curs.fetchall()

        # If unlocked and not set to expire highlight in green
        if locked_or_unlocked == 0:
            print('<tr bgcolor=#e6ffe6><td>')
        # If locked or set to expire highlight in red
        else:
            print('<tr bgcolor=#ffffcc><td>')
        print('<input type="radio" name="selectuser" value="' + uniqname + '">')
        print('</td><td>')
        print('<input type="checkbox" name="togglelock" value="' + uniqname + '">')
        print('</td><td>')
        print(firstname)
        print('</td><td>')
        print(lastname)
        print('</td><td>')
        print(uniqname)
        print('</td><td>')
        print('<input type="text" name="email_' + uniqname + '" value="' + email + '">')
        print('</td><td>')
        print('<input type="date" name="enddate_' + uniqname + '" value="' + enddate + '">')
        print('</td><td>')
        print('<input type="text" name="groups_' + uniqname + '" value="' + groups[0][1] + '">')
        print('</td></tr>')
      

    print('</table>')
    print('</div>')
    print('</div>')
    print('<div class="footer">')
    print('<button type="submit" name="updateusers">Update fields for selected user</button>')
    print('</div>')
    print('</body>')
    print('</html>')

db.close()
