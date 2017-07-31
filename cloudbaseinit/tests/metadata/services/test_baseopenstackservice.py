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

import posixpath
import unittest

try:
    import unittest.mock as mock
except ImportError:
    import mock

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.metadata.services import base
from cloudbaseinit.metadata.services import baseopenstackservice
from cloudbaseinit.tests.metadata import fake_json_response
from cloudbaseinit.utils import x509constants


CONF = cloudbaseinit_conf.CONF

MODPATH = "cloudbaseinit.metadata.services.baseopenstackservice"


class FinalBaseOpenStackService(baseopenstackservice.BaseOpenStackService):

    def _get_data(self):
        pass


class TestBaseOpenStackService(unittest.TestCase):

    def setUp(self):
        CONF.set_override("retry_count_interval", 0)
        self._service = FinalBaseOpenStackService()
        date = "2013-04-04"
        fake_metadata = fake_json_response.get_fake_metadata_json(date)
        self._fake_network_config = fake_metadata["network_config"]
        self._fake_content = self._fake_network_config["debian_config"]
        self._fake_public_keys = fake_metadata["public_keys"]
        self._fake_keys = fake_metadata["keys"]

    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_cache_data")
    def test_get_content(self, mock_get_cache_data):
        response = self._service.get_content('fake name')
        path = posixpath.join('openstack', 'content', 'fake name')
        mock_get_cache_data.assert_called_once_with(path)
        self.assertEqual(mock_get_cache_data.return_value, response)

    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_cache_data")
    def test_get_user_data(self, mock_get_cache_data):
        response = self._service.get_user_data()
        path = posixpath.join('openstack', 'latest', 'user_data')
        mock_get_cache_data.assert_called_once_with(path)
        self.assertEqual(mock_get_cache_data.return_value, response)

    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_cache_data")
    def test_get_meta_data(self, mock_get_cache_data):
        mock_get_cache_data.return_value = '{"fake": "data"}'
        response = self._service._get_meta_data(
            version='fake version')
        path = posixpath.join('openstack', 'fake version', 'meta_data.json')
        mock_get_cache_data.assert_called_with(path, decode=True)
        self.assertEqual({"fake": "data"}, response)

    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_cache_data")
    def test_get_network_data(self, mock_get_cache_data):
        mock_get_cache_data.return_value = '{"fake": "data"}'
        response = self._service._get_network_data(
            version='fake version')
        path = posixpath.join('openstack', 'fake version', 'network_data.json')
        mock_get_cache_data.assert_called_with(path, decode=True)
        self.assertEqual({"fake": "data"}, response)

    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_meta_data")
    def test_get_instance_id(self, mock_get_meta_data):
        response = self._service.get_instance_id()
        mock_get_meta_data.assert_called_once_with()
        mock_get_meta_data().get.assert_called_once_with('uuid')
        self.assertEqual(mock_get_meta_data.return_value.get.return_value,
                         response)

    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_meta_data")
    def test_get_host_name(self, mock_get_meta_data):
        response = self._service.get_host_name()
        mock_get_meta_data.assert_called_once_with()
        mock_get_meta_data().get.assert_called_once_with('hostname')
        self.assertEqual(mock_get_meta_data.return_value.get.return_value,
                         response)

    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_meta_data")
    def test_get_public_keys(self, mock_get_meta_data):
        mock_get_meta_data.return_value.get.side_effect = \
            [self._fake_public_keys, self._fake_keys]
        response = self._service.get_public_keys()

        mock_get_meta_data.assert_called_once_with()
        mock_get_meta_data.return_value.get.assert_any_call("public_keys")
        mock_get_meta_data.return_value.get.assert_any_call("keys")

        public_keys = (list(self._fake_public_keys.values()) +
                       [key["data"] for key in self._fake_keys
                        if key["type"] == "ssh"])
        public_keys = [key.strip() for key in public_keys]

        self.assertEqual(sorted(list(set(public_keys))),
                         sorted(response))

    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_meta_data")
    def _test_get_admin_password(self, mock_get_meta_data, meta_data):
        mock_get_meta_data.return_value = meta_data
        response = self._service.get_admin_password()
        mock_get_meta_data.assert_called_once_with()
        if meta_data and 'admin_pass' in meta_data:
            self.assertEqual(meta_data['admin_pass'], response)
        elif meta_data and 'admin_pass' in meta_data.get('meta'):
            self.assertEqual(meta_data.get('meta')['admin_pass'], response)
        else:
            self.assertIsNone(response)

    def test_get_admin_pass(self):
        self._test_get_admin_password(meta_data={'admin_pass': 'fake pass'})

    def test_get_admin_pass_in_meta(self):
        self._test_get_admin_password(
            meta_data={'meta': {'admin_pass': 'fake pass'}})

    def test_get_admin_pass_no_pass(self):
        self._test_get_admin_password(meta_data={})

    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_meta_data")
    @mock.patch(MODPATH +
                ".BaseOpenStackService.get_user_data")
    def _test_get_client_auth_certs(self, mock_get_user_data,
                                    mock_get_meta_data, meta_data,
                                    ret_value=None):
        mock_get_meta_data.return_value = meta_data
        mock_get_user_data.side_effect = [ret_value]
        response = self._service.get_client_auth_certs()
        mock_get_meta_data.assert_called_once_with()
        if isinstance(ret_value, bytes) and ret_value.startswith(
                x509constants.PEM_HEADER.encode()):
            mock_get_user_data.assert_called_once_with()
            self.assertEqual([ret_value.decode()], response)
        elif ret_value is base.NotExistingMetadataException:
            self.assertFalse(response)
        else:
            expected = []
            expectation = {
                "meta": 'fake cert',
                "keys": [key["data"].strip() for key in self._fake_keys
                         if key["type"] == "x509"]
            }
            for field, value in expectation.items():
                if field in meta_data:
                    expected.extend(value if isinstance(value, list)
                                    else [value])
            self.assertEqual(sorted(list(set(expected))), sorted(response))

    def test_get_client_auth_certs(self):
        self._test_get_client_auth_certs(
            meta_data={'meta': {'admin_cert0': 'fake ',
                                'admin_cert1': 'cert'},
                       "keys": self._fake_keys})

    def test_get_client_auth_certs_no_cert_data(self):
        self._test_get_client_auth_certs(
            meta_data={}, ret_value=x509constants.PEM_HEADER.encode())

    def test_get_client_auth_certs_no_cert_data_exception(self):
        self._test_get_client_auth_certs(
            meta_data={}, ret_value=base.NotExistingMetadataException)

    @mock.patch(MODPATH +
                ".BaseOpenStackService._parse_network_data")
    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_network_data")
    def test_get_network_details(self, mock_get_network_data,
                                 mock_parse_network):
        result = self._service.get_network_details()
        mock_parse_network.assert_called_once_with(mock_get_network_data())
        self.assertEqual(result, mock_parse_network())

    @mock.patch(MODPATH +
                ".BaseOpenStackService._parse_legacy_network_data")
    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_network_data")
    @mock.patch(MODPATH +
                ".BaseOpenStackService.get_content")
    @mock.patch(MODPATH +
                ".BaseOpenStackService._get_meta_data")
    def _test_get_network_details_legacy(self,
                                         mock_get_meta_data,
                                         mock_get_content,
                                         mock_get_network_data,
                                         mock_parse_legacy,
                                         network_config=None,
                                         content=None,
                                         no_path=None):
        # mock obtained data
        mock_get_network_data.return_value = None
        mock_get_meta_data().get.return_value = network_config
        mock_get_content.return_value = content
        ret = self._service.get_network_details()

        mock_get_network_data.assert_called_once_with()
        mock_get_meta_data().get.assert_called_once_with("network_config")
        if network_config and not no_path:
            mock_get_content.assert_called_once_with("network")
        if no_path or not network_config:
            self.assertIsNone(ret)
            return

        self.assertEqual(mock_parse_legacy(), ret)

    def test_get_network_details_no_config(self):
        self._test_get_network_details_legacy(
            network_config=None,
            content=self._fake_content
        )

    def test_get_network_details_no_path(self):
        self._fake_network_config.pop("content_path", None)
        self._test_get_network_details_legacy(
            network_config=self._fake_network_config,
            no_path=True,
            content=self._fake_content
        )

    def test_get_network_details_legacy(self):
        self._test_get_network_details_legacy(
            network_config=self._fake_network_config,
            content=self._fake_content
        )

    @mock.patch(MODPATH +
                ".BaseOpenStackService._parse_l4_network_data")
    @mock.patch(MODPATH +
                ".BaseOpenStackService._parse_l3_network_data")
    @mock.patch(MODPATH +
                ".BaseOpenStackService._parse_l2_network_data")
    def test_parse_network_data(self, mock_parse_l2, mock_parse_l3,
                                mock_parse_l4):
        network_data = "fake network data"
        result = self._service._parse_network_data(network_data)
        mock_parse_l2.assert_called_once_with(network_data)
        mock_parse_l3.assert_called_once_with(network_data, mock_parse_l2())
        mock_parse_l4.assert_called_once_with(network_data)
        advanced_network_details = base.AdvancedNetworkDetails(
            mock_parse_l2(), mock_parse_l3(), mock_parse_l4())
        self.assertEqual(result, advanced_network_details)

    def test_parse_l2_network_data(self):
        network_data = {
            'links': [
                {
                    'id': fake_json_response.NAME0,
                    'type': 'bond',
                    'bond_links': 'fake link 0',
                    'bond_mode': 'fake mode 0',
                    'mtu': 'fake mtu 0',
                    'ethernet_mac_address': fake_json_response.MAC0.upper()
                },
                {
                    'id': fake_json_response.NAME1,
                    'type': 'ovs',
                },
                {
                    'type': 'vlan',
                }
            ]
        }

        # layer 2 config
        l2_config_0 = base.L2NetworkDetails.copy()
        l2_config_0['name'] = fake_json_response.NAME0
        l2_config_0['mac_address'] = fake_json_response.MAC0.upper()
        l2_config_0['type'] = 'bond'
        l2_config_0['bond_info']['bond_members'] = 'fake link 0'
        l2_config_0['bond_info']['bond_mode'] = 'fake mode 0'
        l2_config_0['meta_type'] = 'bond'
        l2_config_0['mtu'] = 'fake mtu 0'

        l2_config_1 = base.L2NetworkDetails.copy()
        l2_config_1['name'] = fake_json_response.NAME1
        l2_config_1['type'] = 'phy'
        l2_config_1['meta_type'] = 'ovs'

        l2_config_2 = base.L2NetworkDetails.copy()
        l2_config_2['type'] = 'vlan'
        l2_config_2['meta_type'] = 'vlan'

        result = self._service._parse_l2_network_data(network_data)
        self.assertDictEqual(result[0], l2_config_0)
        self.assertDictEqual(result[1], l2_config_1)
        self.assertDictEqual(result[2], l2_config_2)

    def test_parse_l3_network_data(self):
        l2_config = [
            {
                'name': 'fake link name',
                'mac_address': fake_json_response.MAC0},
            {}
        ]
        network_data = {
            'networks': [
                {
                    'id': fake_json_response.NAME0,
                    'network_id': 'fake network id',
                    'type': 'ipv4',
                    'link': 'fake link name',
                    'ip_address': fake_json_response.ADDRESS0,
                    'netmask': fake_json_response.NETMASK0,
                    'routes': [{
                        'netmask': '0.0.0.0',
                        'network': '0.0.0.0',
                        'gateway': fake_json_response.GATEWAY0
                    }]
                },
                {
                    'ip_address': '/'.join([fake_json_response.ADDRESS60,
                                            fake_json_response.NETMASK60])
                }
            ]
        }

        # layer 3 config
        l3_config_0 = base.L3NetworkDetails.copy()
        l3_config_0['id'] = 'fake network id'
        l3_config_0['name'] = fake_json_response.NAME0
        l3_config_0['type'] = 'ipv4'
        l3_config_0['meta_type'] = 'ipv4'
        l3_config_0['link_name'] = 'fake link name'
        l3_config_0['mac_address'] = fake_json_response.MAC0
        l3_config_0['ip_address'] = fake_json_response.ADDRESS0
        l3_config_0['netmask'] = fake_json_response.NETMASK0
        l3_config_0['routes'] = network_data['networks'][0]['routes']
        l3_config_0['gateway'] = fake_json_response.GATEWAY0

        l3_config_1 = base.L3NetworkDetails.copy()
        l3_config_1['ip_address'] = fake_json_response.ADDRESS60
        l3_config_1['prefix'] = fake_json_response.NETMASK60

        result = self._service._parse_l3_network_data(network_data, l2_config)

        self.assertDictEqual(result[0], l3_config_0)
        self.assertDictEqual(result[1], l3_config_1)

    def test_parse_l4_network_data(self):
        network_data = {
            "services": [
                {
                    "type": "dns",
                    "address": fake_json_response.DNSNS0.split(' ')[0]
                }
            ]
        }

        result = self._service._parse_l4_network_data(network_data)
        l4_config = base.L4NetworkDetails.copy()
        l4_config['global_dns_nameservers'] = [fake_json_response.DNSNS0
                                               .split(' ')[0]]
        self.assertDictEqual(result, l4_config)

    def test_parse_layers_network_no_data(self):
        self.assertIsNone(self._service._parse_l2_network_data(None))
        self.assertIsNone(self._service._parse_l3_network_data(None, None))
        self.assertIsNone(self._service._parse_l4_network_data(None))
        self.assertIsNone(self._service._parse_network_data(None))
        self.assertIsNone(self._service._parse_legacy_network_data(None))

    def test_parse_legacy_network_data(self):
        mock_iface = mock.Mock()
        mock_iface.mac = fake_json_response.MAC0.upper()
        mock_iface.name = fake_json_response.NAME0
        mock_iface.address = fake_json_response.ADDRESS0
        mock_iface.netmask = fake_json_response.NETMASK0
        mock_iface.gateway = fake_json_response.GATEWAY0
        mock_iface.dnsnameservers = fake_json_response.DNSNS0
        mock_iface.address6 = fake_json_response.ADDRESS60
        mock_iface.netmask6 = fake_json_response.NETMASK60
        mock_iface.gateway6 = fake_json_response.GATEWAY60

        parsed_link = base.L2NetworkDetails.copy()
        parsed_link['type'] = 'phy'
        parsed_link['id'] = mock_iface.name
        parsed_link['name'] = mock_iface.name
        parsed_link['mac_address'] = mock_iface.mac

        parsed_network_ipv4 = base.L3NetworkDetails.copy()
        parsed_network_ipv4['type'] = 'ipv4'
        parsed_network_ipv4['mac_address'] = mock_iface.mac
        parsed_network_ipv4['ip_address'] = mock_iface.address
        parsed_network_ipv4['netmask'] = mock_iface.netmask
        parsed_network_ipv4['gateway'] = mock_iface.gateway
        parsed_network_ipv4['dns_nameservers'] = mock_iface.dnsnameservers

        parsed_network_ipv6 = base.L3NetworkDetails.copy()
        parsed_network_ipv6['type'] = 'ipv6'
        parsed_network_ipv6['mac_address'] = mock_iface.mac
        parsed_network_ipv6['ip_address'] = mock_iface.address6
        parsed_network_ipv6['prefix'] = mock_iface.netmask6
        parsed_network_ipv6['gateway'] = mock_iface.gateway6

        advanced_network_details = base.AdvancedNetworkDetails(
            [parsed_link], [parsed_network_ipv4, parsed_network_ipv6], None)

        result = self._service._parse_legacy_network_data([mock_iface])
        self.assertEqual(result, advanced_network_details)
