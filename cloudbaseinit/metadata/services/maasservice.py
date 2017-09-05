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

import copy
import json
import netaddr
import re

from oauthlib import oauth1
from oslo_log import log as oslo_logging
import requests

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.metadata.services import base
from cloudbaseinit.utils import x509constants

CONF = cloudbaseinit_conf.CONF
LOG = oslo_logging.getLogger(__name__)


class _Realm(str):
    # There's a bug in oauthlib which ignores empty realm strings,
    # by checking that the given realm is always True.
    # This string class always returns True in a boolean context,
    # making sure that an empty realm can be used by oauthlib.
    def __bool__(self):
        return True

    __nonzero__ = __bool__


class MaaSHttpService(base.BaseHTTPMetadataService):
    _METADATA_2012_03_01 = '2012-03-01'

    def __init__(self):
        super(MaaSHttpService, self).__init__(
            base_url=CONF.maas.metadata_base_url,
            https_allow_insecure=CONF.maas.https_allow_insecure,
            https_ca_bundle=CONF.maas.https_ca_bundle)
        self._enable_retry = True
        self._metadata_version = self._METADATA_2012_03_01

    def load(self):
        super(MaaSHttpService, self).load()

        if not CONF.maas.metadata_base_url:
            LOG.debug('MaaS metadata url not set')
        else:
            try:
                self._get_cache_data('%s/meta-data/' % self._metadata_version)
                return True
            except Exception as ex:
                LOG.exception(ex)
                LOG.debug('Metadata not found at URL \'%s\'' %
                          CONF.maas.metadata_base_url)
        return False

    def _get_oauth_headers(self, url):
        LOG.debug("Getting authorization headers for %s.", url)
        client = oauth1.Client(
            CONF.maas.oauth_consumer_key,
            client_secret=CONF.maas.oauth_consumer_secret,
            resource_owner_key=CONF.maas.oauth_token_key,
            resource_owner_secret=CONF.maas.oauth_token_secret,
            signature_method=oauth1.SIGNATURE_PLAINTEXT)
        realm = _Realm("")
        headers = client.sign(url, realm=realm)[1]
        return headers

    def _http_request(self, url, data=None, headers=None):
        """Get content for received url."""
        if not url.startswith("http"):
            url = requests.compat.urljoin(self._base_url, url)
        headers = {} if headers is None else headers
        headers.update(self._get_oauth_headers(url))

        return super(MaaSHttpService, self)._http_request(url, data, headers)

    def get_host_name(self):
        return self._get_cache_data('%s/meta-data/local-hostname' %
                                    self._metadata_version, decode=True)

    def get_instance_id(self):
        return self._get_cache_data('%s/meta-data/instance-id' %
                                    self._metadata_version, decode=True)

    def get_public_keys(self):
        return self._get_cache_data('%s/meta-data/public-keys' %
                                    self._metadata_version,
                                    decode=True).splitlines()

    def get_client_auth_certs(self):
        certs_data = self._get_cache_data('%s/meta-data/x509' %
                                          self._metadata_version,
                                          decode=True)
        pattern = r"{begin}[\s\S]+?{end}".format(
            begin=x509constants.PEM_HEADER,
            end=x509constants.PEM_FOOTER)
        return re.findall(pattern, certs_data)

    def get_user_data(self):
        return self._get_cache_data('%s/user-data' % self._metadata_version)

    def _get_network_data(self):
        data = self._get_cache_data('%s/network_data.json' %
                                    self._metadata_version,
                                    decode=True)
        if data:
            return json.loads(data)

    def get_network_details(self):
        network_data = self._get_network_data()
        if network_data:
            return self._parse_network_data(network_data)

    def _parse_network_data(self, network_data):
        if not network_data:
            return None
        network_l2_config = self._parse_l2_network_data(network_data)
        network_l3_config = self._parse_l3_network_data(network_data,
                                                        network_l2_config)
        network_l4_config = self._parse_l4_network_data(network_data)
        return base.AdvancedNetworkDetails(network_l2_config,
                                           network_l3_config,
                                           network_l4_config)

    def _parse_l2_network_data(self, network_data):
        if not (network_data and network_data.get('config')):
            return None
        parsed_links = []
        for link in network_data['config']:
            if link.get('type') in ['nameserver']:
                continue
            parsed_link = copy.deepcopy(base.L2NetworkDetails)
            parsed_link['name'] = link.get('id')
            parsed_link['mtu'] = link.get('mtu')
            if link.get('mac_address'):
                parsed_link['mac_address'] = link['mac_address'].upper()
            if link.get('type'):
                parsed_link['meta_type'] = link['type']
                parsed_link['type'] = 'phy'
                if link['type'] in ['ovs', 'vif']:
                    parsed_link['type'] = 'phy'
                elif link['type'] in ['vlan']:
                    parsed_link['type'] = link['type']
                    parsed_link['vlan_info']['vlan_id'] = link.get('vlan_id')
                elif link['type'] == 'bond':
                    parsed_link['type'] = link['type']
                    parsed_link['bond_info']['bond_members'] = \
                        link.get('bond_interfaces')
                    if link.get('params') and link['params'].get('bond-mode'):
                        parsed_link['bond_info']['bond_mode'] = \
                            link['params']['bond-mode']
            parsed_links.append(parsed_link)
        return parsed_links

    def _parse_l3_network_data(self, network_data, network_l2_config):
        if not (network_data and network_data.get('config')):
            return None
        parsed_networks = []
        for network_config in network_data['config']:
            if not network_config.get('subnets'):
                continue
            for subnet in network_config.get('subnets'):
                parsed_network = copy.deepcopy(base.L3NetworkDetails)
                parsed_network["id"] = network_config.get('name')
                parsed_network["name"] = network_config.get('name')
                parsed_network['gateway'] = subnet.get('gateway')
                if network_config.get('mac_address'):
                    parsed_network['mac_address'] = \
                        network_config['mac_address'].upper()
                if subnet.get('address'):
                    parsed_network['prefix'] = subnet['address'].split('/')[1]
                    parsed_network['netmask'] = (str(netaddr.IPNetwork(subnet
                                                 ['address']).netmask))
                    parsed_network['ip_address'] = (subnet['address']
                                                    .split('/')[0])
                    version = (netaddr.IPAddress(parsed_network['ip_address'])
                               .version)
                    if version == 4:
                        parsed_network['type'] = 'ipv4'
                    elif version == 6:
                        parsed_network['type'] = 'ipv6'
                parsed_network['meta_type'] = parsed_network['type']
                if subnet.get('dns_nameservers'):
                    parsed_network['dns_nameservers'].extend(
                        subnet['dns_nameservers'])
                parsed_networks.append(parsed_network)
        return parsed_networks

    def _parse_l4_network_data(self, network_data):
        if not (network_data and network_data.get('config')):
            return None
        l4_config = copy.deepcopy(base.L4NetworkDetails)
        for service in network_data['config']:
            if service.get('type') == 'nameserver':
                l4_config['global_dns_nameservers'] = service['address']
                break
        return l4_config
