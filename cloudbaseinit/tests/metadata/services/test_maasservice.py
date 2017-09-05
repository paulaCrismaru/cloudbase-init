# Copyright 2014 Cloudbase Solutions Srl
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
from cloudbaseinit.metadata.services import base
from cloudbaseinit.metadata.services import maasservice
from cloudbaseinit.tests import testutils
from cloudbaseinit.utils import x509constants


CONF = cloudbaseinit_conf.CONF

NAME0 = "eth0"
MAC0 = "fa:16:3e:2d:ec:cd"
ADDRESS = "10.0.0.15"
NETMASK0 = "255.255.255.0"
NETMASK_PREFIX = "24"
GATEWAY = "10.0.0.1"
DNSNS = "208.67.220.220"

NAME1 = "eth1"
MAC1 = "fa:16:3e:2d:ec:ce"
ADDRESS6 = "2001:db8::3"
NETMASK6 = "ffff:ffff:ffff:ffff::"
NETMASK_PREFIX6 = "64"
GATEWAY6 = "2001:db8::1"

BOND = "bond0"
BOND_MODE = "802.3ad"

BOND_VLAN = "bond0.8"
VLAN_ID = 8
ADDRESS2 = "10.0.0.16"
NETMASK2 = "255.255.255.0"
NETMASK_PREFIX2 = "24"

NETWORK_DETAILS = {
    "config": [
        {
            "subnets": [
                {
                    "gateway": GATEWAY,
                    "type": "static",
                    "address": ADDRESS + "/" + NETMASK_PREFIX,
                    "dns_nameservers": [DNSNS]
                }
            ],
            "mac_address": MAC0,
            "type": "physical",
            "mtu": 1500,
            "name": NAME0,
            "id": NAME0
        },
        {
            "subnets": [
                {
                    "gateway": GATEWAY6,
                    "type": "static",
                    "address": ADDRESS6 + "/" + NETMASK6,
                    "dns_nameservers": []
                }
            ],
            "mac_address": MAC1,
            "type": "vif",
            "mtu": 1500,
            "name": NAME1,
            "id": NAME1
        },
        {
            "subnets": [
                {
                    "type": "manual"
                }
            ],
            "type": "bond",
            "id": BOND,
            "params": {
                "bond-mode": BOND_MODE,
                "bond-miimon": 100,
                "bond-lacp_rate": "slow",
                "bond-xmit_hash_policy": "layer2+3",
                "bond-downdelay": 0,
                "bond-updelay": 0
            },
            "mac_address": MAC0,
            "mtu": 1500,
            "name": BOND,
            "bond_interfaces": [NAME0, NAME1]
        },
        {
            "subnets": [
                {
                    "dns_nameservers": [],
                    "type": "static",
                    "address": ADDRESS2 + "/" + NETMASK_PREFIX2
                }
            ],
            "vlan_link": BOND,
            "name": BOND_VLAN,
            "type": "vlan",
            "id": BOND_VLAN,
            "vlan_id": VLAN_ID,
            "mtu": 1500
        },
        {
            "type": "nameserver",
            "address": [DNSNS],
            "search": [
                "maas"
            ]
        }
    ],
    "version": 1
}


class MaaSHttpServiceTest(unittest.TestCase):

    def setUp(self):
        self._maasservice = maasservice.MaaSHttpService()

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def _test_load(self, mock_get_cache_data, ip, cache_data_fails=False):
        if cache_data_fails:
            mock_get_cache_data.side_effect = Exception

        with testutils.ConfPatcher('metadata_base_url', ip, "maas"):
            with testutils.LogSnatcher('cloudbaseinit.metadata.services.'
                                       'maasservice') as snatcher:
                response = self._maasservice.load()

            if ip is not None:
                if not cache_data_fails:
                    mock_get_cache_data.assert_called_once_with(
                        '%s/meta-data/' % self._maasservice._metadata_version)
                    self.assertTrue(response)
                else:
                    expected_logging = 'Metadata not found at URL \'%s\'' % ip
                    self.assertEqual(expected_logging, snatcher.output[-1])
            else:
                self.assertFalse(response)

    def test_load(self):
        self._test_load(ip='196.254.196.254')

    def test_load_no_ip(self):
        self._test_load(ip=None)

    def test_load_get_cache_data_fails(self):
        self._test_load(ip='196.254.196.254', cache_data_fails=True)

    @testutils.ConfPatcher('oauth_consumer_key', 'consumer_key', "maas")
    @testutils.ConfPatcher('oauth_consumer_secret', 'consumer_secret', "maas")
    @testutils.ConfPatcher('oauth_token_key', 'token_key', "maas")
    @testutils.ConfPatcher('oauth_token_secret', 'token_secret', "maas")
    def test_get_oauth_headers(self):
        response = self._maasservice._get_oauth_headers(url='196.254.196.254')
        self.assertIsInstance(response, dict)
        self.assertIn('Authorization', response)

        auth = response['Authorization']
        self.assertTrue(auth.startswith('OAuth'))

        auth = auth[6:]
        parts = [item.strip() for item in auth.split(",")]
        auth_parts = dict(part.split("=") for part in parts)

        required_headers = {
            'oauth_token',
            'oauth_consumer_key',
            'oauth_signature',
        }
        self.assertTrue(required_headers.issubset(set(auth_parts)))
        self.assertEqual('"token_key"', auth_parts['oauth_token'])
        self.assertEqual('"consumer_key"', auth_parts['oauth_consumer_key'])
        self.assertEqual('"consumer_secret%26token_secret"',
                         auth_parts['oauth_signature'])

    @mock.patch('cloudbaseinit.metadata.services.base.'
                'BaseHTTPMetadataService._http_request')
    @mock.patch('cloudbaseinit.metadata.services.maasservice.MaaSHttpService'
                '._get_oauth_headers')
    def test_http_request(self, mock_ouath_headers, mock_http_request):
        mock_url = "fake.url"
        self._maasservice._http_request(mock_url)
        mock_http_request.assert_called_once_with(mock_url, None, {})

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def test_get_host_name(self, mock_get_cache_data):
        response = self._maasservice.get_host_name()
        mock_get_cache_data.assert_called_once_with(
            '%s/meta-data/local-hostname' %
            self._maasservice._metadata_version,
            decode=True)
        self.assertEqual(mock_get_cache_data.return_value, response)

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def test_get_instance_id(self, mock_get_cache_data):
        response = self._maasservice.get_instance_id()
        mock_get_cache_data.assert_called_once_with(
            '%s/meta-data/instance-id' % self._maasservice._metadata_version,
            decode=True)
        self.assertEqual(mock_get_cache_data.return_value, response)

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def test_get_public_keys(self, mock_get_cache_data):
        public_keys = [
            "fake key 1",
            "fake key 2"
        ]
        public_key = "\n".join(public_keys) + "\n"
        mock_get_cache_data.return_value = public_key
        response = self._maasservice.get_public_keys()
        mock_get_cache_data.assert_called_with(
            '%s/meta-data/public-keys' % self._maasservice._metadata_version,
            decode=True)
        self.assertEqual(public_keys, response)

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def test_get_client_auth_certs(self, mock_get_cache_data):
        certs = [
            "{begin}\n{cert}\n{end}".format(
                begin=x509constants.PEM_HEADER,
                end=x509constants.PEM_FOOTER,
                cert=cert)
            for cert in ("first cert", "second cert")
        ]
        mock_get_cache_data.return_value = "\n".join(certs) + "\n"
        response = self._maasservice.get_client_auth_certs()
        mock_get_cache_data.assert_called_with(
            '%s/meta-data/x509' % self._maasservice._metadata_version,
            decode=True)
        self.assertEqual(certs, response)

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def test_get_user_data(self, mock_get_cache_data):
        response = self._maasservice.get_user_data()
        mock_get_cache_data.assert_called_once_with(
            '%s/user-data' %
            self._maasservice._metadata_version)
        self.assertEqual(mock_get_cache_data.return_value, response)

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def test_get_network_data(self, mock_get_cache_data):
        mock_get_cache_data.return_value = json.dumps(NETWORK_DETAILS)
        result = self._maasservice._get_network_data()
        self.assertEqual(NETWORK_DETAILS, result)

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_network_data")
    def _test_get_network_details(self, mock_get_network_data,
                                  network_data, expected_network_details):
        mock_get_network_data.return_value = network_data

        result = self._maasservice.get_network_details()
        self.assertEqual(expected_network_details, result)

    def test_get_network_details(self):
        expected_l2 = [
            {
                'name': NAME0,
                'type': 'phy',
                'meta_type': 'physical',
                'mac_address': MAC0.upper(),
                'mtu': 1500,
                'bond_info': {
                    'bond_members': [],
                    'bond_mode': None
                },
                'vlan_info': {
                    'vlan_id': None
                }
            },
            {
                'name': NAME1,
                'type': 'phy',
                'meta_type': 'vif',
                'mac_address': MAC1.upper(),
                'mtu': 1500,
                'bond_info': {
                    'bond_members': [],
                    'bond_mode': None
                },
                'vlan_info': {
                    'vlan_id': None
                }
            },
            {
                'name': BOND,
                'type': "bond",
                'meta_type': 'bond',
                'mac_address': MAC0.upper(),
                'mtu': 1500,
                'bond_info': {
                    'bond_members': [NAME0, NAME1],
                    'bond_mode': BOND_MODE
                },
                'vlan_info': {
                    'vlan_id': None
                }
            },
            {
                'name': BOND_VLAN,
                'type': "vlan",
                'meta_type': 'vlan',
                'mac_address': None,
                'mtu': 1500,
                'bond_info': {
                    'bond_members': [],
                    'bond_mode': None
                },
                'vlan_info': {
                    'vlan_id': VLAN_ID
                }
            }
        ]
        expected_l3 = [
            {
                'id': NAME0,
                'name': NAME0,
                'type': "ipv4",
                'meta_type': 'ipv4',
                'mac_address': MAC0.upper(),
                'ip_address': ADDRESS,
                'prefix': NETMASK_PREFIX,
                'gateway': GATEWAY,
                'netmask': NETMASK0,
                'dns_nameservers': [DNSNS]
            },
            {
                'id': NAME1,
                'name': NAME1,
                'type': "ipv6",
                'meta_type': 'ipv6',
                'mac_address': MAC1.upper(),
                'ip_address': ADDRESS6,
                'prefix': NETMASK6,
                'gateway': GATEWAY6,
                'netmask': NETMASK6,
                'dns_nameservers': []
            },
            {
                'id': BOND,
                'name': BOND,
                'type': None,
                'meta_type': None,
                'mac_address': MAC0.upper(),
                'ip_address': None,
                'prefix': None,
                'gateway': None,
                'netmask': None,
                'dns_nameservers': []
            },
            {
                'id': BOND_VLAN,
                'name': BOND_VLAN,
                'type': 'ipv4',
                'meta_type': 'ipv4',
                'mac_address': None,
                'ip_address': ADDRESS2,
                'prefix': NETMASK_PREFIX2,
                'gateway': None,
                'netmask': NETMASK2,
                'dns_nameservers': []
            }
        ]
        expected_l4 = {
            'global_dns_nameservers': [DNSNS],
        }
        expected_network_details = base.AdvancedNetworkDetails(
            expected_l2, expected_l3, expected_l4)
        self._test_get_network_details(
            network_data=NETWORK_DETAILS,
            expected_network_details=expected_network_details)

    def test_get_network_no_config(self):
        expected_network_details = base.AdvancedNetworkDetails(
            None, None, None)
        network_details = {"fake": "data"}
        self._test_get_network_details(
            network_data=network_details,
            expected_network_details=expected_network_details)

    def test_get_network_no_data(self):
        self._test_get_network_details(
            network_data=None, expected_network_details=None)

    def test_parse_no_network_data(self):
        self.assertIsNone(self._maasservice._parse_network_data(None))
