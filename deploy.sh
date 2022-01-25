#!/bin/bash

# User Manager deployment script

#
# Clean up, deploy initial directory structure and README
#

if [ "$1" == "core" ]; then
    rm -rf /opt/usermanager/bin
    mkdir -p /opt/usermanager/{bin,etc}
    cp README.md /opt/usermanager

    #
    # Deploy CGI
    #

    rm -rf /usr/lib/cgi-bin/usermanager
    mkdir -p /usr/lib/cgi-bin/usermanager
    cp administrator_dashboard.py /usr/lib/cgi-bin/usermanager
    cp approver_dashboard.py /usr/lib/cgi-bin/usermanager
    cp scan_and_create.py /usr/lib/cgi-bin/usermanager
    cp usermanager_form_handler.py /usr/lib/cgi-bin/usermanager
    cp .htaccess /usr/lib/cgi-bin/usermanager

    #
    # Deploy utility modules, account create and disable modules
    #

    cp scan_and_create.py /opt/usermanager/bin
    cp scan_and_disable.py /opt/usermanager/bin
    cp usermanager_importer.py /opt/usermanager/bin
    cp usermanager_home_agent.py /opt/usermanager/bin

    if [ ! -f /opt/usermanager/etc/usermanager.ini ]; then
        cp usermanager.ini /opt/usermanager/etc
        chmod 644 /opt/usermanager/etc/usermanager.ini
    fi

    #
    # Deploy Web form
    #

    rm -rf /var/www/usermanager
    mkdir -p /var/www/usermanager
    cp index.html /var/www/usermanager
    cp style.css /var/www/usermanager
    cp logo.png /var/www/usermanager
    cp .htaccess /var/www/usermanager

elif [ "$1" == "homeagent" ]; then
    rm -rf /opt/usermanager/bin
    mkdir -p /opt/usermanager/{bin,etc}
    cp README.md /opt/usermanager

    #
    # Deploy home directory agent only
    #

    cp usermanager_home_agent.py /opt/usermanager/bin

    #
    # Deploy configuration
    #

    if [ ! -f /opt/usermanager/etc/usermanager.ini ]; then
        cp usermanager.ini /opt/usermanager/etc
        chmod 600 /opt/usermanager/etc/usermanager.ini
    fi

else
    echo "Usage: deploy.sh {core|homeagent}"
fi
