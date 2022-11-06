# User Manager

### TODO

1. Create utility to export users table to CSV file so it can be easily reviewed by people using Excel

2. Integrate breadcrumbs or some way to easily flip between available dashboards without having to remember a bunch of URLs

3. Possibly update dashboards to permit changing approver and role.

### Installation

To run User Manager, we require:

* An LDAP server with Apache, SSL and Cosign configured as well
* A MySQL database server (separate or same server as above)
* At least one NFS server hosting home directories

On the MySQL server:

1. Create database and user account for User Manager

On the LDAP and HTTP(S) server:

1. Run ```deploy.sh core```

2. Install Cosign (if required) and configure

3. Edit User Manager configuration file

4. Set up database schema

```
/opt/usermanager/bin/setup_schema.py
```

5. Add scan_and_create, scan_and_disable and scan_and_unlock_trained to crontab as root

```
0,5,10,15,20,25,30,35,40,45,50,55    *    *    *    *    /opt/usermanager/bin/scan_and_create.py
0,5,10,15,20,25,30,35,40,45,50,55    *    *    *    *    /opt/usermanager/bin/scan_and_disable.py
0,5,10,15,20,25,30,35,40,45,50,55    *    *    *    *    /opt/usermanager/bin/scan_and_unlock_trained.py
```

On each server that will host home directories:

1. Run ```deploy.sh homeagent```

2. Add home_agent to crontab as root

```
0,5,10,15,20,25,30,35,40,45,50,55    *    *    *    *    /opt/usermanager/bin/usermanager_home_agent.py
```

### MySQL configuration

Set up users table:

```
CREATE TABLE users (
    serialnum integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
    uniqname varchar(16),
    uidnumber integer,
    firstname varchar(64),
    lastname varchar(64),
    emailaddress varchar(128),
    title varchar(128),
    startdate varchar(16),
    enddate varchar(16),
    approver varchar(16),
    requestor varchar(16),
    reason varchar(255),
    role varchar(64),              # Added this field
    approved boolean,
    rejected boolean,              # Added this field
    created boolean,
    expired boolean,
    locked boolean,
    reactivate boolean)            # Added this field
```

Set up groups table:

```
CREATE TABLE groups (
    serialnum integer NOT NULL PRIMARY KEY,
    memberof varchar(1024))
```

Set up homes table:

```
CREATE TABLE homes (
    serialnum integer NOT NULL PRIMARY KEY,
    host varchar(64),
    path varchar(128),
    created boolean)
```

Set up trainings table:

```
CREATE TABLE trainings (
    serialnum integer NOT NULL PRIMARY KEY,
    topmed_user boolean,
    dce101_comp boolean,
    itse106_comp boolean,
    held_pending boolean,
    held_since varchar(16),
    send_reminder boolean)
```

### OpenID Connect configuration

Add to the non-SSL site definition:

```
RewriteRule ^/usermanager https://%{SERVER_NAME}/usermanager/ [R=301,L]
RewriteRule ^usermanager/(.*)$ https://%{SERVER_NAME}/usermanager/$1 [R=301,L]
RewriteRule ^/cgi-bin/usermanager https://%{SERVER_NAME}/usermanager/ [R=301,L]
RewriteRule ^/cgi-bin/usermanager/(.*)$ https://%{SERVER_NAME}/usermanager/$1 [R=301,L]
```

Add to the SSL site definition:

```
<Directory "/usr/lib/cgi-bin/usermanager">
    AuthType openid-connect
    Require valid-user
    SSLRequireSSL
</Directory>

<Directory /var/www/usermanager>
    AuthType openid-connect
    Require valid-user
    SSLRequireSSL
</Directory>

<Directory /usermanager>
    AuthType openid-connect
    Require valid-user
    SSLRequireSSL
</Directory>
```

The .htaccess file at /var/www/usermanager/index.html should look like:

```
AuthType openid-connect
Require valid-user
```

We put the same .htaccess file in /usr/lib/cgi-bin/usermanager

Edit /etc/apache2/sites-enabled/000-default.conf and change:

```
<Directory "/usr/lib/cgi-bin">
    AllowOverride None
    Options +ExecCGI -MultiViews +SymLinksIfOwnerMatch
    Order allow,deny
    Allow from all
</Directory>
```

To read:

```
<Directory "/usr/lib/cgi-bin">
    AllowOverride All
    Options +ExecCGI -MultiViews +SymLinksIfOwnerMatch
    Order allow,deny
    Allow from all
</Directory>
```

Also modify the SSL site definition /etc/apache2/sites-enabled/default-ssl to read the same:

```
<Directory "/usr/lib/cgi-bin">
    AllowOverride All
    Options +ExecCGI -MultiViews +SymLinksIfOwnerMatch
    Order allow,deny
    Allow from all
</Directory>
```

### Cosign configuration

Add to the non-SSL site definition:

```
RewriteRule ^/usermanager https://%{SERVER_NAME}/usermanager/ [R=301,L]
RewriteRule ^usermanager/(.*)$ https://%{SERVER_NAME}/usermanager/$1 [R=301,L]
RewriteRule ^/cgi-bin/usermanager https://%{SERVER_NAME}/usermanager/ [R=301,L]
RewriteRule ^/cgi-bin/usermanager/(.*)$ https://%{SERVER_NAME}/usermanager/$1 [R=301,L]
```

Add to the SSL site definition:

```
<Directory "/usr/lib/cgi-bin/usermanager">
    CosignProtected On
    SSLRequireSSL
</Directory>

<Directory /var/www/usermanager>
    CosignProtected On
    SSLRequireSSL
</Directory>

<Directory /usermanager>
    CosignProtected On
    SSLRequireSSL
</Directory>
```

The .htaccess file at /var/www/usermanager/index.html should look like:

```
CosignProtected On
AuthType Cosign
Require valid-user
```

We put the same .htaccess file in /usr/lib/cgi-bin/usermanager

Edit /etc/apache2/sites-enabled/000-default.conf and change:

```
<Directory "/usr/lib/cgi-bin">
    AllowOverride None
    Options +ExecCGI -MultiViews +SymLinksIfOwnerMatch
    Order allow,deny
    Allow from all
</Directory>
```

To read:

```
<Directory "/usr/lib/cgi-bin">
    AllowOverride All
    Options +ExecCGI -MultiViews +SymLinksIfOwnerMatch
    Order allow,deny
    Allow from all
</Directory>
```

Also modify the SSL site definition /etc/apache2/sites-enabled/default-ssl to read the same:

```
<Directory "/usr/lib/cgi-bin">
    AllowOverride All
    Options +ExecCGI -MultiViews +SymLinksIfOwnerMatch
    Order allow,deny
    Allow from all
</Directory>
```

