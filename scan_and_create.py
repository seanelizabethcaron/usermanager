#!/usr/bin/python3

#
# Requires packages: python3-ldap, python3-mysqldb
#

import os,cgi,time,ldap,MySQLdb,configparser,smtplib,string,random
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

emailreceipt = cfg.getboolean('email', 'emailreceipt')
emailreceiptdir = cfg.get('email', 'emailreceiptdir')

newaccount_tpl = cfg.get('email', 'newaccount_tpl')

# Set umask such that both root and www-data can write to logfiles
os.umask(0o011)

if debug:
    debuglog = open(debug_log_file, 'a+')

if audit:
    auditlog = open(audit_log_file, 'a+')

# Connect to the database
db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

# Pull a list of freshly approved accounts that we need to create
curs = db.cursor()
query = 'SELECT * FROM users WHERE approved = 1 and created = 0;'
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
    role = row[12]

    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': Scan and create processing account request:\n')
        debuglog.write(debug_time + ':     Serial = ' + str(serialnum) + '\n')
        debuglog.write(debug_time + ':     Uniqname = ' + uniqname + '\n')
        debuglog.write(debug_time + ':     UID = ' + str(uidnumber) + '\n')
        debuglog.write(debug_time + ':     First name = ' + firstname + '\n')
        debuglog.write(debug_time + ':     Last name = ' + lastname + '\n')

    # Get the intended home directory for the account
    curs = db.cursor()
    query = 'SELECT * FROM homes WHERE serialnum = ' + str(serialnum) + ';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    report = curs.fetchone()
    homedir = report[2]

    # Get the list of intended group memberships for the account
    curs = db.cursor()
    query = 'SELECT * from groups where serialnum = ' + str(serialnum) + ';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    report = curs.fetchone()
    groups = report[1]

    # Generate a random password for the account
    randomPassword = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))

    # Start assembling the LDAP record
    dn = 'uid=' + uniqname + ',ou=People,dc=csg,dc=sph,dc=umich,dc=edu'

    attrs = {}
    attrs['uid'] = uniqname.encode()
    attrs['uidNumber'] = str(uidnumber).encode()
    attrs['gidNumber'] = '1007'.encode()
    cn_t = firstname + ' ' + lastname
    attrs['cn'] = cn_t.encode()
    attrs['givenName'] = firstname.encode()
    attrs['sn'] = lastname.encode()
    gecos_t = firstname + ' ' + lastname
    attrs['gecos'] = gecos_t.encode()
    attrs['homeDirectory'] = homedir.encode()
    attrs['loginShell'] = '/bin/bash'.encode()
    attrs['shadowMax'] = '99999'.encode()
    attrs['shadowWarning'] = '7'.encode()
    attrs['userPassword'] = randomPassword.encode()
    attrs['objectclass'] = [b'gosaAccount', b'inetOrgPerson', b'organizationalPerson', b'posixAccount', b'top', b'shadowAccount', b'person']

    ldif = modlist.addModlist(attrs)

    # Bind to LDAP
    l = ldap.initialize('ldap://' + private_ldap_host + ':389/')
    l.simple_bind_s(private_ldap_adminuser, private_ldap_adminpass)

    # Add the user account to LDAP
    l.add_s(dn, ldif)

    # We need to add a snippet of code here to update statgen-users with the new user.
    modl = [(ldap.MOD_ADD, 'memberUid', [uniqname.encode()])]
    # Make adding to statgen-users a default in the form, not forced default in this script.
    #l.modify_s('cn=statgen-users,ou=Groups,dc=csg,dc=sph,dc=umich,dc=edu', modl)

    # Also add the user to any other groups specified at the time of request submission.
    # We assume if people are supposed to be in statgen-users, it will be in this list of groups.
    group_list = [group.strip() for group in groups.split(',')]

    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': Unrolling requested group list: ')
        for group in group_list:
            debuglog.write(group + ' ')
        debuglog.write('\n')

    # Set up LDAP search parameters
    baseDN = private_ldap_group_basedn
    searchScope = ldap.SCOPE_SUBTREE
    retrieveAttributes = ["cn"]

    # For each group, check that it exists in LDAP before we attempt to add a user to it
    for group in group_list:
        searchFilter = "cn=" + group
        ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        result_set = []

        while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    result_set.append(result_data)

        if result_set != []:
            if audit:
                audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                auditlog.write(audit_time + ': Adding ' + uniqname + ' to group ' + group + '\n')

            l.modify_s('cn=' + group + ',' + private_ldap_group_basedn, modl)

    # Unbind from the LDAP directory
    l.unbind_s()

    # Check to see if the account should be locked held pending completion of MAIS LINC training modules
    # We need to do this after creating the account in LDAP because accounts are locked by appending an exclamation
    #  point to the password hash and we need this hash to exist in LDAP before we can append to it.

    curs = db.cursor()
    query = 'SELECT held_pending FROM trainings WHERE serialnum = ' + str(serialnum) + ';'
    curs.execute(query)
    held_pending = curs.fetchone()

    if held_pending[0]:
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

    # Add the user to the SLURM accounting database
    acct_desc = 'description=\"' + firstname + ' ' + lastname + '\"'

    # Create the account in SLURM
    os.spawnlp(os.P_WAIT, '/usr/cluster/bin/sacctmgr', '/usr/cluster/bin/sacctmgr', '-i', '-Q', 'add', 'account', uniqname, acct_desc, 'organization=\"csg\"')

    # Wait a few seconds to make sure that SLURM finished creating the account
    time.sleep(5)

    # Assign the user to the account that we just created
    acct_assign = 'account=' + uniqname
    def_acct_assign = 'defaultaccount=' + uniqname

    os.spawnlp(os.P_WAIT, '/usr/cluster/bin/sacctmgr', '/usr/cluster/bin/sacctmgr', '-i', '-Q', 'create', 'user', uniqname, acct_assign, def_acct_assign, 'qoslevel=normal', 'defaultqos=normal')

    # See if the user will have a Samba account created. If so then add the randomPassword to the smbpasswd_mailbox table record for that user and set the ready flag to TRUE
    #  so that scan_and_create will process it
    curs = db.cursor()
    query = 'SELECT * from smbpasswd_mailbox where uniqname = \'' + uniqname + '\' AND ready = 0;'
    curs.execute(query)
    result = curs.fetchone()
    
    if result != None:
        curs = db.cursor()
        query = 'UPDATE smbpasswd_mailbox SET password = \'' + randomPassword + '\' where uniqname = \'' + uniqname + '\';'
        curs.execute(query)
        db.commit()
        
        curs = db.cursor()
        query = 'UPDATE smbpasswd_mailbox SET ready = 1 where uniqname = \'' + uniqname + '\';'
        curs.execute(query)
        db.commit()
        
    # Update the database to note the account having been created
    curs = db.cursor()
    query = 'UPDATE users SET created = 1 where uniqname = \'' + uniqname + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    db.commit()
    
    # Update the audit log
    if audit:
        audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        auditlog.write(audit_time + ': Scan and create successfully added account ' + uniqname + ' to LDAP\n')

    # Dynamically generate a list of suggested hosts for the email text
    node_or_nodes = 'node'
    if role == 'abecasis_user' or role == 'boehnke_user':
        suggested_hosts = '<tt>snowwhite.sph.umich.edu</tt><br><tt>dumbo.sph.umich.edu</tt><br><tt>fantasia.sph.umich.edu</tt><br><tt>wonderland.sph.umich.edu</tt>'
        node_or_nodes = 'nodes'
    elif role == 'alumni_user':
        suggested_hosts = '<tt>csgalumni.sph.umich.edu</tt>'
    elif role == 'external_user':
        suggested_hosts = '<tt>sandbox.sph.umich.edu</tt>'
    elif role == 'mukherjee_user' or role == 'fritsche_user':
        suggested_hosts = '<tt>junglebook.sph.umich.edu</tt>'
    elif role == 'kardiasmith_user':
        suggested_hosts = '<tt>orion.sph.umich.edu</tt>'
    elif role == 'psoriasis_user':
        suggested_hosts = '<tt>psoriasis.sph.umich.edu</tt>'
    elif role == 'willer_user':
        suggested_hosts = '<tt>hunt.sph.umich.edu</tt>'
    elif role == 'zhou_user':
        suggested_hosts = '<tt>mulan.sph.umich.edu</tt>'
    else:
        suggested_hosts = '<tt>snowwhite.sph.umich.edu</tt><br><tt>dumbo.sph.umich.edu</tt><br><tt>fantasia.sph.umich.edu</tt><br><tt>wonderland.sph.umich.edu</tt>'

    # Send an e-mail to the new user with initial account information
    with open(newaccount_tpl) as tp:
        lines = tp.read()

    tpl = Template(lines)

    emailtext = tpl.substitute(FIRSTNAME=firstname, UNIQNAME=uniqname, RANDOMPASSWORD=randomPassword, NODEORNODES=node_or_nodes, SUGGESTED_HOSTS=suggested_hosts)

    msg = MIMEMultipart('alternative')

    msg['Subject'] = 'New CSG cluster account information for ' + uniqname
    msg['From'] = 'do-not-reply@umich.edu'
    msg['To'] = email

    part1 = MIMEText(emailtext, 'html')

    msg.attach(part1)

    s = smtplib.SMTP('localhost')
    s.sendmail('do-not-reply@umich.edu', email, msg.as_string())
    s.quit()

    if emailreceipt:
        receiptfile = emailreceiptdir + '/' + uniqname + '.receipt.txt'
        receipt = open(receiptfile, 'a+')
        receipt.write(emailtext)
        receipt.close()

# Pull a list of accounts marked for reactivation that need to be unlocked
curs = db.cursor()
query = 'SELECT * FROM users WHERE reactivate = 1;'
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

    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': Attempting to reactivate user account ' + uniqname + '\n')

    # Bind to LDAP
    l = ldap.initialize('ldap://' + private_ldap_host + ':389/')
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
    unlocked_pwd = user_password.replace("}!", "}")

    # Write back the updated password to LDAP to unlock the account
    modl = [(ldap.MOD_REPLACE, 'userPassword', [unlocked_pwd])]
    l.modify_s(dn, modl)

    # Unbind from the LDAP directory
    l.unbind_s()

    # Update the database to flip the reactivate flag off since we are done
    curs = db.cursor()
    query = 'UPDATE users SET reactivate = 0 where uniqname = \'' + uniqname + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    db.commit()

    # Update the audit log
    if audit:
        audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        auditlog.write(audit_time + ': Scan and disable successfully reactivated account ' + uniqname + '\n')

# Close audit log
if audit:
    auditlog.close()

# Close debug log
if debug:
    debuglog.close()
