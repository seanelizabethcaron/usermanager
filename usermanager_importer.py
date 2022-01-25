#!/usr/bin/python

import csv, ldap, ConfigParser, MySQLdb, time, sys, os

cfg = ConfigParser.ConfigParser()
cfg.read('/opt/usermanager/etc/usermanager.ini')

dbuser = cfg.get('database', 'user')
dbpass = cfg.get('database', 'passwd')
dbname = cfg.get('database', 'db')
dbhost = cfg.get('database', 'host')
audit = cfg.getboolean('logging', 'audit')
debug = cfg.getboolean('logging', 'debug')
audit_log_file = cfg.get('logging', 'auditlog')
debug_log_file = cfg.get('logging', 'debuglog')

private_ldap_host = cfg.get('privateldap', 'host')

private_ldap_user_basedn = cfg.get('privateldap', 'user_basedn')
private_ldap_group_basedn = cfg.get('privateldap', 'group_basedn')

private_ldap_adminuser = cfg.get('privateldap', 'adminuser')
private_ldap_adminpass = cfg.get('privateldap', 'adminpass')

campus_ldap_host = cfg.get('campusldap', 'host')
campus_ldap_basedn = cfg.get('campusldap', 'basedn')

# Set umask such that both root and www-data can write to logfiles
os.umask(0o011)

if debug:
    debuglog = open(debug_log_file, 'a+')

if audit:
    auditlog = open(audit_log_file, 'a+')

# Connect to the database
db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

with open('csg_user_account_audit_sheet.csv') as csvfile:
    rdr = csv.reader(csvfile, quotechar='|')
    for row in rdr:
        active_or_locked = row[0]
        uniqname = row[1]
        firstname = row[2]
        lastname = row[3]
        email = row[4]
        title = row[5]
        requestor = row[6]
        startdate = row[9]
        expdate = row[10]

        # There are no equivalents to some fields in the old audit sheet so we will just set the values as static
        approver = 'scaron'
        reason = 'Imported'
        role = 'user'

        l = ldap.initialize('ldap://' + private_ldap_host + ':389')
        l.protocol_version = ldap.VERSION3
        baseDN = private_ldap_user_basedn
        searchScope = ldap.SCOPE_SUBTREE
        retrieveAttributes = ["uidNumber", "homeDirectory"]
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

        if (result_set == []):
            print('Could not find record in LDAP for user ' + uniqname + ' to dereference to UID number. Skipping import of this user.\n')
            if debug:
                debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                debuglog.write(debug_time + ': No LDAP record for user ' + uniqname + ' to dereference UID number. Skipping import of this user.\n')
            #sys.exit(0)
        else:
            # Extract display name, UID number and home directory from LDAP query response
            dn, results = result_set[0][0]
            #display_name = results['displayName'][0]
            uid_number = results['uidNumber'][0]
            homedir = results['homeDirectory'][0]

            # Determine home directory host from full home directory path
            if 'dumbo' in homedir:
                home_host = 'dumbo'
            elif 'snowwhite' in homedir:
                home_host = 'snowwhite'
            elif 'fantasia' in homedir:
                home_host = 'fantasia'
            elif 'wonderland' in homedir:
                home_host = 'wonderland'
            elif 'mulan' in homedir:
                home_host = 'mulan'
            elif 'hunt' in homedir:
                home_host = 'hunt'
            elif 'twins' in homedir:
                home_host = 'twins'
            elif 'csgalumni' in homedir:
                home_host = 'csgalumni'
            elif 'sandbox' in homedir:
                home_host = 'sandbox'
            elif 'assembly' in homedir:
                home_host = 'assembly'
            elif 'schuylkill' in homedir:
                home_host = 'schuylkill'
            elif 'psoriasis' in homedir:
                home_host = 'psoriasis'
            elif 'frodo' in homedir:
                home_host = 'frodo'
            elif 'mgi' in homedir:
                home_host = 'mgi'
            else:
                home_host = 'undefined'

            # Try to dump all the groups that the user is a member of
            baseDN = private_ldap_group_basedn
            searchScope = ldap.SCOPE_SUBTREE
            retrieveAttributes = ["cn"]
            #searchFilter = '(|(&(objectClass=posixGroup)(memberUid=' + uniqname + ',' + private_ldap_user_basedn + ')))'
            searchFilter = '(|(&(objectClass=posixGroup)(memberUid=' + uniqname + ')))'
            ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
            result_set = []
            while 1:
                result_type, result_data = l.result(ldap_result_id, 0)
                if (result_data == []):
                    break
                else:
                    if result_type == ldap.RES_SEARCH_ENTRY:
                        result_set.append(result_data)

            print(uniqname)
            groups = ''
            for res in result_set:
                grp = res[0][1]['cn'][0]
                groups = groups + grp + ','

            groups = groups[:-1]
            print(groups)

            # Active account
            if active_or_locked == 'A':
                print('ACT Uniqname = ' + uniqname + ' UID = ' + str(uid_number) + ' First = ' + firstname + ' Last = ' + lastname + ' Email = ' + email + ' Title = ' + title + ' Home = ' + homedir + ' Start date = ' + startdate + ' Exp date = ' + expdate + '\n')

                curs = db.cursor()
                query = 'INSERT INTO users (uniqname,uidnumber,firstname,lastname,emailaddress,title,startdate,enddate,approver,requestor,reason,role,approved,rejected,created,expired,locked,reactivate) VALUES (\'' + uniqname + '\',' + str(uid_number) + ',\'' + firstname + '\',\'' + lastname + '\',\'' + email + '\',\'' + title + '\',\'' + startdate + '\',\'' + expdate + '\',\'' + approver + '\',\'' + requestor + '\',\'' + reason + '\',\'' + role + '\',1,0,1,0,0,0);'
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
                query = 'INSERT INTO homes (serialnum, host, path, created) VALUES (' + str(found_serialnum) + ', \'' + home_host + '\',\'' + homedir + '\', 1);'
                if debug:
                    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
                curs.execute(query)
                db.commit()

                # Add groups to the groups table
                curs = db.cursor()
                query = 'INSERT INTO groups (serialnum, memberof) VALUES (' + str(found_serialnum) + ', \'' + groups + '\');'
                if debug:
                    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
                curs.execute(query)
                db.commit()

            # Locked account
            else:
                print('LCK Uniqname = ' + uniqname + ' UID = ' + str(uid_number) + ' First = ' + firstname + ' Last = ' + lastname + ' Email = ' + email + ' Title = ' + title + ' Home = ' + homedir + ' Start date = ' + startdate + ' Exp date = ' + expdate + '\n')

                curs = db.cursor()
                query = 'INSERT INTO users (uniqname,uidnumber,firstname,lastname,emailaddress,title,startdate,enddate,approver,requestor,reason,role,approved,rejected,created,expired,locked,reactivate) VALUES (\'' + uniqname + '\',' + str(uid_number) + ',\'' + firstname + '\',\'' + lastname + '\',\'' + email + '\',\'' + title + '\',\'' + startdate + '\',\'' + expdate + '\',\'' + approver + '\',\'' + requestor + '\',\'' + reason + '\',\'' + role + '\',1,0,1,1,1,0);'
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
                query = 'INSERT INTO homes (serialnum, host, path, created) VALUES (' + str(found_serialnum) + ', \'' + home_host + '\',\'' + homedir + '\', 1);'
                if debug:
                    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
                curs.execute(query)
                db.commit()

                # Add groups to the groups table
                curs = db.cursor()
                query = 'INSERT INTO groups (serialnum, memberof) VALUES (' + str(found_serialnum) + ', \'' + groups + '\');'
                if debug:  
                    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
                curs.execute(query)
                db.commit()

