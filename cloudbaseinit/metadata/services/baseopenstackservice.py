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
import posixpath

from oslo_log import log as oslo_logging

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.metadata.services import base
from cloudbaseinit.utils import debiface
from cloudbaseinit.utils import encoding
from cloudbaseinit.utils import x509constants

CONF = cloudbaseinit_conf.CONF
LOG = oslo_logging.getLogger(__name__)


class BaseOpenStackService(base.BaseMetadataService):

    def get_content(self, name):
        path = posixpath.normpath(
            posixpath.join('openstack', 'content', name))
        return self._get_cache_data(path)

    def get_user_data(self):
        path = posixpath.normpath(
            posixpath.join('openstack', 'latest', 'user_data'))
        return self._get_cache_data(path)

    def _get_network_data(self, version='latest'):
        path = posixpath.normpath(
            posixpath.join('openstack', version, 'network_data.json'))
        data = self._get_cache_data(path, decode=True)
        if data:
            return json.loads(data)

    def _get_meta_data(self, version='latest'):
        path = posixpath.normpath(
            posixpath.join('openstack', version, 'meta_data.json'))
        data = self._get_cache_data(path, decode=True)
        if data:
            return json.loads(data)

    def get_instance_id(self):
        return self._get_meta_data().get('uuid')

    def get_host_name(self):
        return self._get_meta_data().get('hostname')

    def get_public_keys(self):
        """Get a list of all unique public keys found among the metadata."""
        public_keys = []
        meta_data = self._get_meta_data()
        public_keys_dict = meta_data.get("public_keys")
        if public_keys_dict:
            public_keys = list(public_keys_dict.values())
        keys = meta_data.get("keys")
        if keys:
            for key_dict in keys:
                if key_dict["type"] == "ssh":
                    public_keys.append(key_dict["data"])
        return list(set((key.strip() for key in public_keys)))

    def get_network_details(self):
        network_data = self._get_network_data()
        if network_data:
            return self._parse_network_data(network_data)
        else:
            network_config = self._get_meta_data().get('network_config')
            if not network_config:
                return None
            key = "content_path"
            if key not in network_config:
                return None

            content_name = network_config[key].rsplit("/", 1)[-1]
            content = self.get_content(content_name)
            content = encoding.get_as_string(content)

            return self._parse_legacy_network_data(debiface.parse(content))

    def _parse_network_data(self, network_data):
        if not network_data:
            return None
        LOG.debug(network_data)
        network_l2_config = self._parse_l2_network_data(network_data)
        LOG.debug(network_l2_config)
        network_l3_config = self._parse_l3_network_data(network_data,
                                                        network_l2_config)
        LOG.debug(network_l3_config)
        network_l4_config = self._parse_l4_network_data(network_data)
        LOG.debug(network_l4_config)
        return base.AdvancedNetworkDetails(network_l2_config,
                                           network_l3_config,
                                           network_l4_config)

    def _parse_legacy_network_data(self, legacy_network_data):
        if not legacy_network_data:
            return
        parsed_links = []
        parsed_networks = []
        for iface in legacy_network_data:
            parsed_link = base.L2NetworkDetails.copy()
            parsed_network_ipv4 = base.L3NetworkDetails.copy()
            parsed_network_ipv6 = base.L3NetworkDetails.copy()
            mac_address = None
            if iface.mac:
                mac_address = iface.mac.upper()

            parsed_link['type'] = 'phy'
            parsed_link['id'] = iface.name
            parsed_link['name'] = iface.name
            parsed_link['mac_address'] = mac_address

            parsed_network_ipv4['type'] = 'ipv4'
            parsed_network_ipv4['mac_address'] = mac_address
            parsed_network_ipv4['ip_address'] = iface.address
            parsed_network_ipv4['netmask'] = iface.netmask
            parsed_network_ipv4['gateway'] = iface.gateway
            parsed_network_ipv4['dns_nameservers'] = iface.dnsnameservers

            parsed_network_ipv6['type'] = 'ipv6'
            parsed_network_ipv6['mac_address'] = mac_address
            parsed_network_ipv6['ip_address'] = iface.address6
            parsed_network_ipv6['prefix'] = iface.netmask6
            parsed_network_ipv6['gateway'] = iface.gateway6

            parsed_links.append(parsed_link)
            parsed_networks.append(parsed_network_ipv4)
            parsed_networks.append(parsed_network_ipv6)

        return base.AdvancedNetworkDetails(parsed_links,
                                           parsed_networks,
                                           None)

    def _parse_l2_network_data(self, network_data):
        if not (network_data and network_data.get('links')):
            return None
        parsed_links = []
        for link in network_data['links']:
            parsed_link = base.L2NetworkDetails.copy()
            if link.get('id'):
                parsed_link['name'] = link['id']

            if link.get('type'):
                parsed_link['meta_type'] = link['type']
                parsed_link['type'] = 'phy'
                if link['type'] in ['ovs', 'vif']:
                    parsed_link['type'] = 'phy'
                elif link['type'] in ['phy', 'vlan']:
                    parsed_link['type'] = link['type']
                elif link['type'] == 'bond':
                    parsed_link['type'] = link['type']
                    bond_info = parsed_link['extra_info']['bond_info']
                    if link.get('bond_links'):
                        bond_info['bond_members'] = link['bond_links']
                    if link.get('bond_mode'):
                        bond_info['bond_mode'] = link['bond_mode']

            if link.get('mtu'):
                parsed_link['mtu'] = link['mtu']
            if link.get('ethernet_mac_address'):
                parsed_link['mac_address'] = (link['ethernet_mac_address']
                                              .upper())
            parsed_links.append(parsed_link)
        return parsed_links

    def _parse_l3_network_data(self, network_data, network_l2_config):
        if not (network_data and network_data.get('networks')):
            return None
        parsed_networks = []
        for network in network_data['networks']:
            parsed_network = base.L3NetworkDetails.copy()
            if network.get('network_id'):
                parsed_network['id'] = network['network_id']
            if network.get('id'):
                parsed_network['name'] = network['id']
            if network.get('type'):
                parsed_network['meta_type'] = network['type']
                if network['type'] in (["ipv4", "ipv6", "ipv4_dhcp",
                                        "ipv6_dhcp"]):
                    parsed_network['type'] = network['type']
            if network.get('link'):
                parsed_network['link_name'] = network['link']
                associated_link = ([x for x in network_l2_config
                                    if x.get('name') == network['link']])
                if associated_link and associated_link[0]['mac_address']:
                    parsed_network['mac_address'] = (associated_link[0]
                                                     .get('mac_address'))
            if network.get('ip_address'):
                ip_address_prefix = network.get('ip_address').split('/')
                if len(ip_address_prefix) == 2:
                    parsed_network['ip_address'] = ip_address_prefix[0]
                    parsed_network['prefix'] = ip_address_prefix[1]
                else:
                    parsed_network['ip_address'] = network.get('ip_address')
            if network.get('netmask'):
                parsed_network['netmask'] = network.get('netmask')
            if network.get('routes'):
                parsed_network['routes'] = network.get('routes')
                route_gateway = (
                    [route for route in network['routes']
                        if (route.get('network') == '0.0.0.0' and
                            route.get('netmask') == '0.0.0.0') or
                           (route.get('network') == '::' and
                            route.get('netmask') == '::')
                     ])
                if route_gateway and route_gateway[0].get('gateway'):
                    parsed_network['gateway'] = route_gateway[0]['gateway']
            parsed_networks.append(parsed_network)

        return parsed_networks

    def _parse_l4_network_data(self, network_data):
        if not (network_data and network_data.get('services')):
            return None
        l4_config = base.L4NetworkDetails.copy()
        for service in network_data['services']:
            if service['type'] == 'dns':
                l4_config['dns_config'].append(service['address'])
        return l4_config

    def get_admin_password(self):
        meta_data = self._get_meta_data()
        meta = meta_data.get('meta')

        if meta and 'admin_pass' in meta:
            password = meta['admin_pass']
        elif 'admin_pass' in meta_data:
            password = meta_data['admin_pass']
        else:
            password = None

        return password

    def get_client_auth_certs(self):
        """Gather all unique certificates found among the metadata.

        If there are no certificates under "meta" or "keys" field,
        then try looking into user-data for this kind of information.
        """
        certs = []
        meta_data = self._get_meta_data()

        meta = meta_data.get("meta")
        if meta:
            cert_data_list = []
            idx = 0
            while True:
                # Chunking is necessary as metadata items can be
                # max. 255 chars long.
                cert_chunk = meta.get("admin_cert%d" % idx)
                if not cert_chunk:
                    break
                cert_data_list.append(cert_chunk)
                idx += 1
            if cert_data_list:
                # It's a list of strings for sure.
                certs.append("".join(cert_data_list))

        keys = meta_data.get("keys")
        if keys:
            for key_dict in keys:
                if key_dict["type"] == "x509":
                    certs.append(key_dict["data"])

        if not certs:
            # Look if the user_data contains a PEM certificate
            try:
                user_data = self.get_user_data().strip()
                if user_data.startswith(
                        x509constants.PEM_HEADER.encode()):
                    certs.append(encoding.get_as_string(user_data))
            except base.NotExistingMetadataException:
                LOG.debug("user_data metadata not present")

        return list(set((cert.strip() for cert in certs)))
