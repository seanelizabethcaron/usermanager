#!/usr/bin/python3

#
# Requires packages: python3-ldap, python3-mysqldb python3-pymssql
#

import csv,ldap,configparser,MySQLdb,time,sys,os,pymssql,datetime,smtplib
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

mais_dbhost = cfg.get('maislinc', 'mais_dbhost')
mais_dbuser = cfg.get('maislinc', 'mais_dbuser')
mais_passwd = cfg.get('maislinc', 'mais_passwd')
mais_dbport = cfg.get('maislinc', 'mais_dbport')
mais_db = cfg.get('maislinc', 'mais_db')

private_ldap_host = cfg.get('privateldap', 'host')
private_ldap_user_basedn = cfg.get('privateldap', 'user_basedn')
private_ldap_adminuser = cfg.get('privateldap', 'adminuser')
private_ldap_adminpass = cfg.get('privateldap', 'adminpass')

audit = cfg.getboolean('logging', 'audit')
debug = cfg.getboolean('logging', 'debug')
audit_log_file = cfg.get('logging', 'auditlog')
debug_log_file = cfg.get('logging', 'debuglog')

complete_dce_tpl = cfg.get('email', 'complete_dce_tpl')
complete_bulkdata_tpl = cfg.get('email', 'complete_bulkdata_tpl')
complete_itse_tpl = cfg.get('email', 'complete_itse_tpl')

# Set umask such that both root and www-data can write to logfiles
os.umask(0o011)

if debug:
    debuglog = open(debug_log_file, 'a+')

if audit:
    auditlog = open(audit_log_file, 'a+')

# Get list of users to check from our local DB

# Connect to the database
local_db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

# Get list of users with held accounts pending completion of training modules
local_curs = local_db.cursor()
query = 'SELECT serialnum,topmed_user,held_since,send_reminder FROM trainings WHERE held_pending = 1;'
local_curs.execute(query)
report = local_curs.fetchall()

# Connect to the MAIS LINC database
mais_dbase = pymssql.connect(server=mais_dbhost, user=mais_dbuser, password=mais_passwd, database=mais_db, port=mais_dbport)
mais_cursor = mais_dbase.cursor()

for username in report:

    # Serialnum is username[0] topmed_user flag is username[1] held_since is username[2] send_reminder is username[3]
    serialnum = username[0]
    topmed_user = username[1]
    held_since = username[2]
    send_reminder = username[3]

    # Get uniqname from serial number
    local_curs = local_db.cursor()
    query = 'SELECT uniqname FROM users WHERE serialnum = ' + str(serialnum) + ';'
    local_curs.execute(query)
    uniqname = local_curs.fetchone()[0]

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

    # Determine PEERRS_DOJ_BulkData_T100 completion status
    query = 'SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk AND b.Code in (\'PEERRS_DOJ_BulkData_T100\') and d.Username in (\'' + uniqname + '\');'

    mais_cursor.execute(query)
    result = mais_cursor.fetchone()

    if result == None:
        bulkdata_completed = 0
    else:
        bulkdata_completed = 1
    
    # Update the local database record with current training completion status
    local_curs = local_db.cursor()
    query = 'UPDATE trainings SET dce101_comp = ' + str(dce101_completed) + ' WHERE serialnum = ' + str(serialnum) + ';'
    local_curs.execute(query)

    local_curs = local_db.cursor()
    query = 'UPDATE trainings SET itse106_comp = ' + str(itse106_completed) + ' WHERE serialnum = ' + str(serialnum) + ';'
    local_curs.execute(query)

    local_curs = local_db.cursor()
    query = 'UPDATE trainings SET bulkdata_comp = ' + str(bulkdata_completed) + ' WHERE serialnum = ' + str(serialnum) + ';'
    local_curs.execute(query)

    # At this point:
    #  If dce_101 completed = TRUE and bulkdata_completed and topmed_user = FALSE then unlock
    #  If dce_101 completed = TRUE and bulkdata_completed and itse106_completed = TRUE and topmed_user = TRUE then unlock
    #  Otherwise check to see if we need to send an email reminder about the training modules

    if dce101_completed and bulkdata_completed and not topmed_user:
        unlock_account = 1
    elif dce101_completed and and bulkdata_completed and itse106_completed and topmed_user:
        unlock_account = 1
    else:
        unlock_account = 0

    if unlock_account:
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
        unlocked_pwd = user_password.decode().replace("}!", "}")

        # Write back the updated password to LDAP to unlock the account
        modl = [(ldap.MOD_REPLACE, 'userPassword', [unlocked_pwd.encode()])]
        l.modify_s(dn, modl)

        # Unbind from the LDAP directory
        l.unbind_s()

        # Update the local database to note the account is no longer being held pending completion of training modules
        local_curs = local_db.cursor()
        query = 'UPDATE trainings SET held_pending = 0 WHERE serialnum = ' + str(serialnum) + ';'
        local_curs.execute(query)

        # Do not send reminders to users that have already completed training modules
        local_curs = local_db.cursor()
        query = 'UPDATE trainings SET send_reminder = 0 WHERE serialnum = ' + str(serialnum) + ';'
        local_curs.execute(query)

        # Reset the held since date with our sentinel value for accounts that are not being held
        local_curs = local_db.cursor()
        query = 'UPDATE trainings SET held_since = \'0000-00-00\' WHERE serialnum = ' + str(serialnum) + ';'
        local_curs.execute(query)

        # Unlock the samba account if applicable

        curs = local_db.cursor()
        query = 'SELECT * from samba where uniqname = \'' + uniqname + '\';'
        curs.execute(query)
        result = curs.fetchone()

        # If the user shows up in the samba table then we know that a Samba account exists for them
        if result != None:
            # Get the home directory host for the account
            curs = local_db.cursor()
            query = 'SELECT * FROM homes WHERE serialnum = ' + str(serialnum) + ';'
            if debug:
                debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
            curs.execute(query)
            report = curs.fetchone()
            home_host = report[1]

            # Create a smbpasswd_workqueue entry to reenable the Samba account of the user
            curs = local_db.cursor()
            query = 'INSERT INTO smbpasswd_workqueue (host, uniqname, action, ready) VALUES (\'' + home_host + '\',\'' + uniqname + '\',\'e\',1);'
            if debug:
                debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
                debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
            curs.execute(query)
            local_db.commit()

        if audit:
            audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            auditlog.write(audit_time + ': Unlocking held account ' + uniqname + ' with confirmed training module completion\n')

    # If the account has not met the training module completion conditions to unlock it
    #  Check the held_since date and if this has been more than 7 days from today, send an email reminder
    else:

        held_yr, held_mo, held_dy = held_since.split('-')

        # Create a datetime object out of the held_since date so we can do some date math on it
        held_since_date = datetime.datetime(int(held_yr), int(held_mo), int(held_dy))

        # Create another datetime object with the current day
        today = datetime.datetime.today()

        # Create a third datetime object to represent the time delta
        seven_days = datetime.timedelta(days=7)

        if (today - held_since_date) > seven_days:
            send_email = 1
        else:
            send_email = 0

        if send_email and send_reminder:
            # Get first name and email address
            local_curs = local_db.cursor()
            query = 'SELECT firstname,emailaddress FROM users WHERE serialnum = ' + str(serialnum) + ';'
            local_curs.execute(query)

            result_set = local_curs.fetchone()
            firstname = result_set[0]
            email = result_set[1]

            # All users need to complete DCE 101
            if not dce101_completed:
                with open(complete_dce_tpl) as tp:
                    lines = tp.read()

                tpl = Template(lines)

                emailtext = tpl.substitute(FIRSTNAME=firstname)
                emailsubj = 'DCE 101 e-learning module completion reminder for ' + uniqname

                # Send the email reminder
                msg = MIMEMultipart('alternative')

                msg['Subject'] = emailsubj
                msg['From'] = 'do-not-reply@umich.edu'
                msg['To'] = email

                part1 = MIMEText(emailtext, 'html')

                msg.attach(part1)

                s = smtplib.SMTP('localhost')
                s.sendmail('do-not-reply@umich.edu', email, msg.as_string())
                s.quit()

             # All users need to complete PEERRS_DOJ_BulkData_T100
             if not bulkdata_completed:
                with open(complete_bulkdata_tpl) as tp:
                    lines = tp.read()

                tpl = Template(lines)

                emailtext = tpl.substitute(FIRSTNAME=firstname)
                emailsubj = 'PEERRS_DOJ_BulkData_T100 e-learning module completion reminder for ' + uniqname

                # Send the email reminder
                msg = MIMEMultipart('alternative')

                msg['Subject'] = emailsubj
                msg['From'] = 'do-not-reply@umich.edu'
                msg['To'] = email

                part1 = MIMEText(emailtext, 'html')

                msg.attach(part1)

                s = smtplib.SMTP('localhost')
                s.sendmail('do-not-reply@umich.edu', email, msg.as_string())
                s.quit()

              # Only FISMA and CUI enclave users need to complete PEERRS_CUI_T100
              if topmed_user and  not itse106_completed:
                with open(complete_itse_tpl) as tp:
                    lines = tp.read()

                tpl = Template(lines)

                emailtext = tpl.substitute(FIRSTNAME=firstname)
                emailsubj = 'PEERRS_CUI_T100 e-learning module completion reminder for ' + uniqname

                # Send the email reminder
                msg = MIMEMultipart('alternative')

                msg['Subject'] = emailsubj
                msg['From'] = 'do-not-reply@umich.edu'
                msg['To'] = email

                part1 = MIMEText(emailtext, 'html')
                msg.attach(part1)

                s = smtplib.SMTP('localhost')
                s.sendmail('do-not-reply@umich.edu', email, msg.as_string())
                s.quit()

            # Update the local database record so we only send one reminder at this time
            local_curs = local_db.cursor()
            query = 'UPDATE trainings SET send_reminder = 0 WHERE serialnum = ' + str(serialnum) + ';'
            local_curs.execute(query)

local_db.commit()
