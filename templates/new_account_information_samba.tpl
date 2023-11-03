<html>
<head>
</head>
<body>
Hi $FIRSTNAME,
<br><br>
Your account on the CSG cluster has been created with the following parameters:
<br><br>
User name: <tt>$UNIQNAME</tt>
<br>
Password: <tt>$RANDOMPASSWORD</tt>
<br><br>
First thing you receive this message, please take 30-60 minutes to sign on to U-M MAIS LINC and complete the <A HREF="https://maislinc.umich.edu/maislinc/app/management/LMS_ActDetails.aspx?UserMode=0&ActivityId=47169">DCE 101: Access and Compliance: Handling Sensitive Institutional Data at U-M</A> e-learning module.
<br><br>
If you are working on the TOPMED project or if you are affiliated with the Kardia-Smith lab, please also complete the MAIS LINC <A HREF="https://maislinc.umich.edu/core/pillarRedirect?relyingParty=LM&url=app%2Fmanagement%2FLMS_ActDetails.aspx%3FActivityId%3D307926%26UserMode%3D0">Securing Controlled Unclassified Information</A> module.
<br><br>
You will need your U-M uniqname password to log in to MAIS LINC to complete the training modules. If you are a sponsored external affiliate and did not receive your U-M uniqname password, please reach out to your collaborator at CSG who is sponsoring your account.
<br><br>
Completing these training modules is mandatory. Your account will be locked until they are recorded as completed and you will not be able to reset your password or log in to any CSG cluster resources.
<br><br>
Second, please take a moment to visit the URL:
<br><br>
<tt><a href="https://csgadmin.sph.umich.edu/gosa">https://csgadmin.sph.umich.edu/gosa</a></tt>
<br><br>
Sign in with your user name and temporary password above, then click the Change password button in the upper right hand corner of the page to reset your cluster password to something of your choice that meets our complexity guidelines.
<br><br>
Finally, if you are new to Linux or cluster computing, introductory documentation regarding the use of the CSG cluster is available at the URL:
<br><br>
<tt><a href="http://csg.sph.umich.edu/cluster-documentation/">http://csg.sph.umich.edu/cluster-documentation</a></tt>
<br><br>
Once you've completed the preliminaries, you will be able to log in to your assigned cluster gateway $NODEORNODES using your favorite SSH client:
<br><br>
$SUGGESTED_HOSTS
<br><br>
Note that if you are working off campus, the University of Michigan now requires the use of the U-M VPN to initiate SSH connections to systems on U-M network
s. Logging in to the U-M VPN will require the use of your U-M uniqname password, which is the same password that you will use to access MAIS LINC and complet
e the required data security training modules. Documentation for the U-M VPN and installers for the U-M VPN client may be found at the following URL:
<br><br>
<tt><a href="https://its.umich.edu/enterprise/wifi-networks/vpn/getting-started">https://its.umich.edu/enterprise/wifi-networks/vpn/getting-started</a></tt>
<br><br>
Your cluster gateway host, $SAMBAHOST, also supports access to file shares from a desktop computer via Samba.
<br><br>
When accessing Samba on $SAMBAHOST, please use the following credentials:
<br><br>
User name: <tt>$SAMBAHOST.sph.umich.edu\$UNIQNAME</tt>
Password: <tt>$RANDOMPASSWORD</tt>
<br><br>
Once you get logged in via SSH, you can run the following command to reset your Samba password to something of your choice with the following command:
<br><br>
<tt>smbpasswd</tt>
<br><br>
Note that due to technical constraints, your cluster login password and Samba password cannot be automatically synchronized on the CSG cluster. You must manage the two passwords separately via their respective mechanisms (though you can use the same password for both).
<br><br>
Please follow best practices when setting your Samba password. A minimum password length of 16 characters is required and the password should include multiple character classes such as uppercase, lowercase, numerals and punctuation.
<br><br>
You must be on a U-M campus network or connected to the U-M VPN to access Samba. You must also have completed the required data security training modules on MAIS LINC as described earlier in this message. If these conditions are satisfied, you may access Samba shares on $SAMBAHOST by hitting the Windows key and typing:
<br><br>
<tt>\\$SAMBAHOST.sph.umich.edu</tt>
<br><br>
If you would like to map a drive letter to the Samba share on $SAMBAHOST, you may do so by following the procedure below:
<br><br>
<a href="https://support.microsoft.com/en-us/windows/map-a-network-drive-in-windows-29ce55d1-34e3-a7e2-4801-131475f9557d">Map a network drive in Windows</a>
<br><br>
Please contact our IT help desk at <a href="mailto:csg.help@umich.edu">csg.help@umich.edu</a> with any questions or trouble.
<br><br>
Best,
<br><br>
CSG Account Administrators
</body>
</html>
