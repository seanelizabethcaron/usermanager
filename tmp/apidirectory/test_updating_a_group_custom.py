import requests
import json
try:
    import urllib.parse
except ImportError:
    import urlparse

import ConfigParser

cfg = ConfigParser.ConfigParser()
cfg.read('/opt/usermanager/etc/usermanager.ini')

clientid = cfg.get('mcommunity', 'clientid')
clientsecret = cfg.get('mcommunity', 'clientsecret')

from apidirectory import ApiDirectory

class IamGroupUpdate:

    client_id = clientid
    secret = clientsecret
    scope = "iamgroups"
    token_url = "https://apigw.it.umich.edu/um/inst/oauth2/token"
    url_base = "https://apigw.it.umich.edu/um/iamGroups"

    groupName = "csg-it-announcements-test"
    groupDn = "cn={},ou=user groups,ou=groups,dc=umich,dc=edu".format(groupName)

    # This will update the group with the supplied values. These web service will replace existing value.
    # For instance the update member replaces all members.
    # warning if you modify the owner you could remove your access.  See the example below.
    def update_group(self, eMailAddress):

        print(eMailAddress)
        eMailUser,eMailHost = eMailAddress.split("@")

        # Internal U-M users
        if "umich.edu" in eMailHost:
            url = "members/" + self.groupDn
            existingMembers = self.get_membership(url)

            stringToAppend = 'uid=' + eMailUser + ',ou=people,dc=umich,dc=edu'
            existingMembers.append(stringToAppend)

            data = {'dn': self.groupDn, 'memberDn': existingMembers}
            self.apply_update(data, "update/member")

        # External non-UM users
        else:
            url = "members/" + self.groupDn
            existingExtMembers =  self.get_external_membership(url)

            newExtMembers = [ ]

            for emailAddress in existingExtMembers:
                newExtMembers.append({'email': emailAddress})

            newExtMembers.append({'email': eMailAddress})

            data = {'dn': self.groupDn, 'memberExternal': newExtMembers}
            self.apply_update(data, "update/externalMember")


    # Sample update method to reduce the repetitiveness in the other examples.
    def apply_update(self, data, url_endpoint):
        print("updating " + url_endpoint)
        api = ApiDirectory(self.client_id, self.secret, self.scope, self.token_url)
        url = IamGroupUpdate.url_base + '/' + url_endpoint
        response = requests.post(
            url=url,
            data=json.dumps(data),
            headers=api.build_headers(),
            timeout=10
        )

        if (response.status_code != requests.codes.ok):
            print('Response: {}'.format(response))
            print('JSON: {}'.format(response.json()))
            raise Exception("issue with update")

        map = response.json()
        return map

    def get_membership(self, url_endpoint):
        print("getting " + url_endpoint)
        api = ApiDirectory(self.client_id, self.secret, self.scope, self.token_url)
        url = IamGroupUpdate.url_base + '/' + url_endpoint
        response = requests.get(
            url=url,
            headers=api.build_headers(),
            timeout=10
        )

        map = response.json()

        return map["group"]["memberDn"]

    def get_external_membership(self, url_endpoint):
        print("getting " + url_endpoint)
        api = ApiDirectory(self.client_id, self.secret, self.scope, self.token_url)
        url = IamGroupUpdate.url_base + '/' + url_endpoint
        response = requests.get(
            url=url,
            headers=api.build_headers(),
            timeout=10
        )

        map = response.json()

        return map["group"]["memberExternalRaw"]

g = IamGroupUpdate()

eMailAddress = "lojulie@umich.edu"

g.update_group(eMailAddress)

eMailAddress = "vern.caron@gmail.com"

g.update_group(eMailAddress)

