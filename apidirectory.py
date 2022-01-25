#
# This Python module is provided by U-M ITS to support interfacing with MCommunity
# Sourced from: https://gitlab.umich.edu/its-inf-iam/iamgroups-examples
#

import requests
import json
import logging

logger = logging.getLogger(__name__)


# Create Two Factor Authentication to the API Directory.
class ApiDirectory:

    # Constructor
    def __init__(self, client_id, secret, scope, token_url, timeout=10):
        self.client_id = client_id
        self.secret = secret
        self.scope = scope
        self.token_url = token_url
        self.timeout = timeout

    # Validates that the minimal values have been set to connect to the API Directory.
    def _validate_initialization(self):
        if (self.client_id is None
            or self.secret is None
            or self.scope is None
            or self.token_url is None):
            raise Exception("Invalid class configuration")

    # internal method to request an access bearer token.
    def _find_token(self):
        data = {
            'grant_type': 'client_credentials',
            'scope': 'constituents'
        }
        headers = {
            'Content-type': 'application/x-www-form-urlencoded',
            'accept': 'application/json'
        }
        url = self.token_url + "?grant_type=client_credentials&scope={}".format(self.scope)

        response = requests.post(
            url,
            data=json.dumps(data),
            headers=headers,
            auth=(self.client_id, self.secret),
            timeout=self.timeout,
        )
        logger.debug('response={} json={}'.format(response, response.json()))

        return response.json()

    # internal method to parse the access token.
    def _find_access_token(self):
        token = self._find_token()
        if ('access_token' in token):
            access_token = token['access_token']
        else:
            logger.debug(token)
            if ('error' in token):
                err = token['error']

            if ('error_description' in token):
                err += ":" + token['error_description']

            if (err is None):
                err = "unknown error"

            raise Exception(err)

        return access_token

    # public method for building the https header needed for calling the API Directory.
    def build_headers(self):
        self._validate_initialization()
        bearer = self._find_access_token()
        return {
            'x-ibm-client-id': '{}'.format(self.client_id),
            'authorization': 'Bearer ' + bearer,
            'accept': 'application/json'
        }

