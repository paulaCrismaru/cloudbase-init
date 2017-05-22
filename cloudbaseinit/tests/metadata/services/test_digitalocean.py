# Copyright 2017 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import json
import unittest

try:
    import unittest.mock as mock
except ImportError:
    import mock

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.metadata.services import digitalocean

CONF = cloudbaseinit_conf.CONF
MOD_PATH = 'cloudbaseinit.metadata.services.digitalocean'
HOSTNAME = "fake hostname"
DROPLET_ID = '123'
PUBLIC_KEYS = ["ssh-rsa key1", "ssh-rsa key2"]
fake_metadata_template = '{{'\
    '"hostname": "{hostname}",'\
    '"droplet_id": {id},'\
    '"public_keys": {keys}'\
    '}}'


class DigitalOceanTest(unittest.TestCase):

    def setUp(self):
        self._digitalocean = digitalocean.DigitalOceanService()
        self.fake_metadata = fake_metadata_template.format(
            hostname=HOSTNAME, id=DROPLET_ID, keys=json.dumps(PUBLIC_KEYS))

    @mock.patch('cloudbaseinit.metadata.services.base.'
                'BaseHTTPMetadataService._get_cache_data')
    def test_load(self, mock_get_cache_data):
        mock_get_cache_data.return_value = self.fake_metadata
        result = self._digitalocean.load()
        self.assertTrue(result)

    @mock.patch('cloudbaseinit.metadata.services.base.'
                'BaseHTTPMetadataService._get_cache_data')
    def test_load_fails(self, mock_get_cache_data):
        mock_get_cache_data.side_effect = Exception("fake exception")
        result = self._digitalocean.load()
        self.assertFalse(result)

    @mock.patch('cloudbaseinit.metadata.services.base.'
                'BaseHTTPMetadataService._get_cache_data')
    def test_get_instance_id(self, mock_get_cache_data):
        mock_get_cache_data.return_value = self.fake_metadata
        result = self._digitalocean.get_instance_id()
        self.assertEqual(result, DROPLET_ID)

    @mock.patch('cloudbaseinit.metadata.services.base.'
                'BaseHTTPMetadataService._get_cache_data')
    def test_get_public_keys(self, mock_get_cache_data):
        mock_get_cache_data.return_value = self.fake_metadata
        result = self._digitalocean.get_public_keys()
        self.assertEqual(sorted(result), sorted(PUBLIC_KEYS))
