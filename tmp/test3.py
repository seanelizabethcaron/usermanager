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

groups = 'statgen-users, topmed , sysads'

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

print('<' + groups + '>')

