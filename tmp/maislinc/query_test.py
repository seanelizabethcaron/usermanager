#!/usr/bin/python3

# Requires packages: python-mssql, python3-mssql
import csv, ldap, configparser, pymssql, time, sys, os

dbhost = 'db-mylprdm.adsroot.itcs.umich.edu'
dbuser = 'RMTSCHOFPH_MYLPRDM1'
passwd = 'g4E2Vbxc!'
dbport = '14330'
db = 'MYLincPRD_UUD'

# Connect to the database

db = pymssql.connect(server=dbhost, user=dbuser, password=passwd, database=db, port=dbport)

curs = db.cursor()

#
# According to ITS support:
# The query that I built to pull the data in the spreadsheet is below. Once you have the
# ID and password you should be able to use it to run this query for whatever course code(s)
# (b.Code) or uniqname(s) (d.Username) that you'd like.
#
# SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt
# FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE
# c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk and
# b.Code in ('DCE101') and d.Username in ('SCARON');
#

# ITS_ITSE106 or DCE101

query = 'SELECT a.PersonNumber, d.Username, b.Code, b.ActivityName, c.score, c.EndDt FROM Person a, TBL_TMX_Activity b, TBL_TMX_Attempt c, UserLogin d WHERE c.EmpFK = a.PersonPK AND c.ActivityFK = b.Activity_PK AND a.PersonPK= d.personfk AND b.Code in (\'PEERRS_CUI_T100\') and d.Username in (\'aprnance\');'

curs.execute(query)
result = curs.fetchone()

if result == None:
    print("User has not completed DCE101")
else:
    print("User has completed DCE101")
    print(result)

#
# If the user has completed DCE101, the query will return a string like:
#
# (u'42390493', u'SCARON', u'DCE101', u'DCE101 Archive Access and Compliance:
# Handling Sensitive Institutional Data at U-M', None, datetime.datetime(2018
# , 2, 21, 21, 14, 28, 410000))
#
# If the user has not completed DCE101, the query will return None
#

