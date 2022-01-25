#!/usr/bin/python

# Requires packages: python-ldap, python-mysqldb
import sys,os,cgi,time,ldap,MySQLdb, ConfigParser, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
private_ldap_adminuser = cfg.get('privateldap', 'adminuser')
private_ldap_adminpass = cfg.get('privateldap', 'adminpass')

campus_ldap_host = cfg.get('campusldap', 'host')
campus_ldap_basedn = cfg.get('campusldap', 'basedn')

# Uniqname to do a query against
#uniqname = "scaron"
uniqname = sys.argv[1]

#l = ldap.open("ldap.itd.umich.edu")
l = ldap.initialize('ldap://' + 'csgadmin.sph.umich.edu' + ':389')
l.protocol_version = ldap.VERSION3
baseDN = private_ldap_user_basedn
searchScope = ldap.SCOPE_SUBTREE
retrieveAttributes = ["uidNumber", "displayName", "cn", "givenName", "sn", "umichTitle"]
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

if (res_set == []):
    print('No uniqname found\n')
    sys.exit(0)

# Extract displayName and uidNumber reported by ITCS LDAP.

dn, results = res_set[0][0]

print(results)

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

uid_number = results['uidNumber'][0]
#umichTitle = results['umichTitle'][0]

if displayType == 'USE_DISPLAYNAME':
    displayName_segments = displayName.split()
    firstName = displayName_segments[0]
    lastName = displayName_segments[-1]
elif displayType == 'USE_CN':
    cn_segments = cn.split()
    firstName = cn_segments[0]
    lastName = cn_segments[-1]
elif displayType == 'USE_GIVENNAME_SN':
    firstName = givenName
    lastName = sn
else:
    firstName = uniqname
    lastName = uniqname

print(firstName)
print(lastName)

print(uid_number)
#print(umichTitle)

