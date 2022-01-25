import logging
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

logger = logging.getLogger(__name__)


class IamGroupUpdateTests:

    client_id = clientid
    secret = clientsecret
    scope = "iamgroups"
    token_url = "https://apigw.it.umich.edu/um/inst/oauth2/token"
    url_base = "https://apigw.it.umich.edu/um/iamGroups"

    groupName = "csg-it-announcements-test"
    groupDn = "cn={},ou=user groups,ou=groups,dc=umich,dc=edu".format(groupName)

    # create a group for the test cases
    def setUp(self):
        api = ApiDirectory(self.client_id, self.secret, self.scope, self.token_url)

        url_endpoint = 'create'
        url = IamGroupUpdateTests.url_base + '/' + url_endpoint
        print('Running setup ' + self.groupName)
        data = {'name': self.groupName}

        response = requests.post(
            url=url,
            data=json.dumps(data),
            headers=api.build_headers(),
            timeout=10
        )

        self.assertEqual(response.status_code, requests.codes.ok)

    # delete the group created for the test.
    def tearDown(self):
        api = ApiDirectory(self.client_id, self.secret, self.scope, self.token_url)
        dn = self.groupDn
        encoded_dn = urllib.parse.quote(dn)
        url_endpoint = 'delete'
        url = IamGroupUpdateTests.url_base + '/' + url_endpoint + "/" + encoded_dn
        print('Running teardown ' + self.groupName)
        response = requests.get(
            url=url,
            headers=api.build_headers(),
            timeout=10
        )
        self.assertEqual(response.status_code, requests.codes.ok)

    # This will update the group with the supplied values. These web service will replace existing value.
    # For instance the update member replaces all members.
    # warning if you modify the owner you could remove your access.  See the example below.
    def test_update_group(self):
        data = {'dn': self.groupDn,
                #'aliases': ['anotherNameTest'],
                #'description': 'Sample test group created and updated from a unit test',
                #'notice': "Test notice",
                #'labeledUri': [{'urlValue': 'yahoo.com'}, {'urlLabel': 'Google', 'urlValue': 'google.com'}],
                # settings
                #'isprivate': 'true',
                #'isjoinable': 'false',
                #'IsSpamBlocked': 'true',
                #'IsEmailableByMembersOnly': 'false',
                #'IsEmailWarningSuppressed': 'true',
                # end settings
                'memberDn': ['uid=cdobski,ou=people,dc=umich,dc=edu'],
                #'memberGroupDn': ['cn=post-its-notes,ou=user groups,ou=groups,dc=umich,dc=edu'],
                #'moderator': [{'email': 'barbara.jensen@yahoo.com'},
                #              {'name': 'Barbara Jensen', 'email': 'bjensen@yahoo.com'}],
                'memberExternal': [{'email': 'someone@google.com'}, {'email': 'someone@yahoo.com', 'name': 'someone'}]
                }

        existingMembers = self.test_get_membership()
        #existingMembers.append('uid=sdushett,ou=people,dc=umich,dc=edu')
        #existingMembers.append('uid=lojulie,ou=people,dc=umich,dc=edu')
        existingMembers.append('uid=dekemar,ou=people,dc=umich,dc=edu')

        existingExtMembers = self.test_get_external_membership()

        #for email in existingExtMembers:
        #    print(email)

        newExtMembers = [ ]
        
        for emailAddress in existingExtMembers:
            newExtMembers.append({'email': emailAddress})

        print newExtMembers
        newExtMembers.append({'email': 'vern.caron@gmail.com'})

        print newExtMembers
 
        #print existingMembers
        #print newExtMembers
 
        #self.apply_update(data, "update/aliases")
        #self.apply_update(data, "update/description")
        #self.apply_update(data, "update/notice")
        #self.apply_update(data, "update/links")
        #self.apply_update(data, "update/settings")
        #self.apply_update(data, "update/member")
        #self.apply_update(data, "update/groupMember")
        #self.apply_update(data, "update/moderator")
        #self.apply_update(data, "update/externalMember")

        data = {'dn': self.groupDn, 'memberDn': existingMembers}
        self.apply_update(data, "update/member")

        data = {'dn': self.groupDn, 'memberExternal': newExtMembers}
        self.apply_update(data, "update/externalMember")

        #data = {'dn': self.groupDn, 'memberExternal': [{'email': 'sean.t.caron@gmail.com'}]}
        #self.apply_update(data, "update/externalMember")

        #data = {'dn': self.groupDn, 'memberDn': ['uid=dhke,ou=people,dc=umich,dc=edu', 'uid=cdobski,ou=people,dc=umich,dc=edu']}
        #self.apply_update(data, "update/member")

    # This example updates a group owner.  First it looks up the group.
    # Adds an owner to the existing group.
    # replace ErrorsTo attribute
    # Adds a Request To attribute
    # This is how the api was designed.  First lookup the group.  Make your modification.  Then submit the changes.
    def update_group_management_attributes(self):

        # lookup the group.
        group = self.lookup(self.groupDn)

        # add owner to the returned group.
        personDn = "uid=bjensen,ou=people,dc=umich,dc=edu"
        group['ownerDn'].append(personDn)
        self.apply_update(group, "update/owner")

        # replace errorto
        group['errorsTo'] = [personDn]
        self.apply_update(group, "update/errorsTo")

        if ('requestTo' in group and group['requestTo'] is not None):
            group['requestTo'].append(personDn)
        else:
            group['requestTo'] = [personDn]

        self.apply_update(group, "update/requestTo")

    # updates the privacy setting for the notice
    def update_privacySettings(self):
        # values for level
        # PUBLIC
        # PROTECTED
        # PRIVATE

        # values for field
        # description
        # notice
        # links
        # membership
        # joinable

        data = {'dn': self.groupDn,
                'level': 'PUBLIC',
                'field': 'notice'
                }

        self.apply_update(data, 'update/privacySetting')

    # Sample update method to reduce the repetitiveness in the other examples.
    def apply_update(self, data, url_endpoint):
        print("updating " + url_endpoint)
        api = ApiDirectory(self.client_id, self.secret, self.scope, self.token_url)
        url = IamGroupUpdateTests.url_base + '/' + url_endpoint
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
        url = IamGroupUpdateTests.url_base + '/' + url_endpoint
        print "test: URL is " + url 
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
        url = IamGroupUpdateTests.url_base + '/' + url_endpoint
        print "test: URL is " + url
        response = requests.get(
            url=url,
            headers=api.build_headers(),
            timeout=10
        )

        map = response.json()

        return map["group"]["memberExternalRaw"]

    def test_get_membership(self):
        url = "members/" + self.groupDn
        return self.get_membership(url)

    def test_get_external_membership(self):
        url = "members/" + self.groupDn
        return self.get_external_membership(url)

    # Sample lookup based on dn to reduce repetitiveness of the other examples.
    def lookup(self, dn):
        api = ApiDirectory(self.client_id, self.secret, self.scope, self.token_url)
        encoded = urllib.parse.quote(dn)
        url_endpoint = 'profile/dn'
        url = IamGroupUpdateTests.url_base + '/' + url_endpoint + "/" + encoded

        response = requests.get(
            url=url,
            headers=api.build_headers(),
            timeout=10
        )

        if (response.status_code != requests.codes.ok):
            print('Response: {}'.format(response))
            print('JSON: {}'.format(response.json()))
            raise Exception("issue with update")

        # note that the returned json is a group object which is a list of profiles
        profile = response.json()['group'][0]
        return profile

g = IamGroupUpdateTests()
g.test_update_group()
#g.test_get_membership()
