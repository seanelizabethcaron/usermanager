#!/usr/bin/python3

#
# Requires packages: python3-ldap, python3-mysqldb
#

import sys,os,subprocess,cgi,time,MySQLdb,configparser,smtplib,string,random,platform,os,shutil,stat,pwd,grp

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

default_permissions = cfg.get('homeagent', 'default_permissions')
default_group = cfg.get('homeagent', 'default_group')

# Set umask such that both root and www-data can write to logfiles
os.umask(0o011)

if debug:
    debuglog = open(debug_log_file, 'a+')

if audit:
    auditlog = open(audit_log_file, 'a+')

# Connect to the database
db = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpass,db=dbname)

# Get the host name of the node where we are running
my_hostname = platform.node()
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': Home directory creation agent found our hostname to be ' + my_hostname + '\n')

# Check to see if we have any accounts with home directories requiring creation
curs = db.cursor()
query = 'SELECT * FROM homes WHERE created = 0 AND host = \'' + my_hostname + '\';'
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
curs.execute(query)
report = curs.fetchall()

for row in report:
    serialnum = row[0]
    home_host = row[1]
    path = row[2]

    # Select the user record corresponding to this serial number and get the uniqname
    curs = db.cursor()
    query = 'SELECT uniqname,created FROM users WHERE serialnum = ' + str(serialnum) + ';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string to find uniqname is ' + query + '\n')
    curs.execute(query)
    report = curs.fetchall()

    uniqname = report[0][0]
    created = report[0][1]

    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': Found uniqname to be ' + uniqname + '\n')

    # Only try to set up the home directory once the account is actually created in LDAP
    if created == 1:
        # Dereference the uniqname to a numeric UID and GID we can use with os.chown()
        #  Double check we can actually resolve this user before proceeding, otherwise exit and wait for the next run
        try:
            uid = pwd.getpwnam(uniqname).pw_uid
        except KeyError:
            sys.exit(0)

        gid = grp.getgrnam(default_group).gr_gid
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': Dereferencing user ' + uniqname + ' to UID ' + str(uid) + ' with GID ' + str(gid) + '\n')

        # Create the home directory
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': Attempting to create home directory ' + path + '\n')
        os.makedirs(path)
        os.chown(path, uid, gid)
        # Convert the default home directory permissions string from the config to an integer interpreted as octal
        permissions = int(default_permissions, 8)
        os.chmod(path, permissions)

        # Create .nedit subdirectory
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': Attempting to create .nedit directory ' + path + '/.nedit\n')
        os.makedirs(path + '/.nedit')
        os.chown(path + '/.nedit', uid, gid)
        os.chmod(path + '/.nedit', stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

        # Copy in .profile
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': Attempting to create .profile file ' + path + '/.profile\n')
        shutil.copy('/usr/cluster/etc/sample.profile', path + '/.profile')
        os.chown(path + '/.profile', uid, gid)
        os.chmod(path + '/.profile', stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

        # Copy in .bashrc
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': Attempting to create .bashrc file ' + path + '/.bashrc\n')
        shutil.copy('/usr/cluster/etc/sample.bashrc', path + '/.bashrc')
        os.chown(path + '/.bashrc', uid, gid)
        os.chmod(path + '/.bashrc', stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

        # Copy in nedit.rc
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': Attempting to create nedit.rc file ' + path + '/.nedit/nedit.rc\n')
        shutil.copy('/usr/cluster/etc/sample.nedit', path + '/.nedit/nedit.rc')
        os.chown(path + '/.nedit/nedit.rc', uid, gid)
        os.chmod(path + '/.nedit/nedit.rc', stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

        # Copy in .nanorc
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': Attempting to create .nanorc file ' + path + '/.nanorc\n')
        shutil.copy('/usr/cluster/etc/sample.nanorc', path + '/.nanorc')
        os.chown(path + '/.nanorc', uid, gid)
        os.chmod(path + '/.nanorc', stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

        # Update the database to reflect the home directory as having been created
        curs = db.cursor()
        query = 'UPDATE homes SET created = 1 where path = \'' + path + '\';'
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
        curs.execute(query)
        db.commit()

        # Update the audit log
        if audit:
            audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            auditlog.write(audit_time + ': Created home directory and dotfiles for user ' + uniqname + '\n')
            
# Check to see if we have any smbpasswd account creation work to do
curs = db.cursor()
query = 'SELECT * FROM smbpasswd_workqueue WHERE ready = 1 AND action = \'a\' AND host = \'' + my_hostname + '\';'
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
curs.execute(query)
report = curs.fetchall()

# For each entry in smbpasswd_workqueue for this host with action add, add a Samba account for that user
for row in report:
    uniqname = row[2]
    password = row[3]
    
    # Prepare the password in the format that smbpasswd expects to be piped
    prepped_password = password + '\n' + password + '\n'
    
    # Create the Samba account for the user with the requisite password
    subprocess.run(["/usr/bin/smbpasswd", "-a", "-s", uniqname], input=prepped_password, text=True, capture_output=False)
    
    # If the user account is locked pending completion of training modules, lock the Samba account after creating it
    
    # Determine the serial number of this user account so we can find it in the trainings table
    curs = db.cursor()
    query = 'SELECT * FROM users WHERE uniqname = \'' + uniqname + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    report = curs.fetchone()
    
    serialnum = report[0]
    
    # Determine if the account is held pending completion of training modules
    curs = db.cursor()
    query = 'SELECT held_pending FROM trainings WHERE serialnum = ' + str(serialnum) + ';'
    curs.execute(query)
    held_pending = curs.fetchone()

    # If so then lock the Samba account until the training modules are completed.
    if held_pending[0]:
        subprocess.run(["/usr/bin/smbpasswd", "-d", uniqname], input=None, text=True, capture_output=False)
        
        # Record the Samba account as being locked in our tracking database
        curs = db.cursor()
        query = 'UPDATE samba SET locked = 1 where uniqname = \'' + uniqname + '\';'
        if debug:
            debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
            debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
        curs.execute(query)
        db.commit()
    
    # Record the Samba account as being created in our tracking database
    curs = db.cursor()
    query = 'UPDATE samba SET created = 1 where uniqname = \'' + uniqname + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    db.commit()
    
    # Remove the task from the smbpasswd_workqueue table since we are finished with it
    curs = db.cursor()
    query = 'DELETE FROM smbpasswd_workqueue WHERE uniqname = \'' + uniqname + '\' AND action = \'a\' AND host = \'' + my_hostname + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    db.commit()

    # Update the audit log
    if audit:
        audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        if held_pending[0]:
            auditlog.write(audit_time + ': Created Samba account for user ' + uniqname + ' (locked pending completion of training)\n')
        else:
            auditlog.write(audit_time + ': Created Samba account for user ' + uniqname + '\n')
            
# Check to see if we have any smbpasswd account disablement work to do
curs = db.cursor()
query = 'SELECT * FROM smbpasswd_workqueue WHERE ready = 1 AND action = \'d\' AND host = \'' + my_hostname + '\';'
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
curs.execute(query)
report = curs.fetchall()

# For each entry in smbpasswd_workqueue for this host with action disable, disable the Samba account for that user
for row in report:
    uniqname = row[2]
    
    # Disable the Samba account for the user
    subprocess.run(["/usr/bin/smbpasswd", "-d", uniqname], input=None, text=True, capture_output=False)
    
    # Record the Samba account as being locked in our tracking database
    curs = db.cursor()
    query = 'UPDATE samba SET locked = 1 where uniqname = \'' + uniqname + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    db.commit()

    # Remove the task from the smbpasswd_workqueue table since we are finished with it
    curs = db.cursor()
    query = 'DELETE FROM smbpasswd_workqueue WHERE uniqname = \'' + uniqname + '\' AND action = \'d\' AND host = \'' + my_hostname + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    db.commit()
    
    # Update the audit log
    if audit:
        audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        auditlog.write(audit_time + ': Disabled Samba account for user ' + uniqname + '\n')

# Check to see if we have any smbpasswd account enablement work to do
curs = db.cursor()
query = 'SELECT * FROM smbpasswd_workqueue WHERE ready = 1 AND action = \'e\' AND host = \'' + my_hostname + '\';'
if debug:
    debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
    debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
curs.execute(query)
report = curs.fetchall()

# For each entry in smbpasswd_workqueue for this host with action enable, enable the Samba account for that user
for row in report:
    uniqname = row[2]
    
    # Enable the Samba account for the user
    subprocess.run(["/usr/bin/smbpasswd", "-e", uniqname], input=None, text=True, capture_output=False)
    
    # Record the Samba account as being unlocked in our tracking database
    curs = db.cursor()
    query = 'UPDATE samba SET locked = 0 where uniqname = \'' + uniqname + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    db.commit()

    # Remove the task from the smbpasswd_workqueue table since we are finished with it
    curs = db.cursor()
    query = 'DELETE FROM smbpasswd_workqueue WHERE uniqname = \'' + uniqname + '\' AND action = \'e\' AND host = \'' + my_hostname + '\';'
    if debug:
        debug_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        debuglog.write(debug_time + ': SQL query string is ' + query + '\n')
    curs.execute(query)
    db.commit()

    # Update the audit log
    if audit:
        audit_time = time.strftime("%A %b %d %H:%M:%S %Z", time.localtime())
        auditlog.write(audit_time + ': Enabled Samba account for user ' + uniqname + '\n')

