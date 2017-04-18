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
import netaddr
import posixpath
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

    def _get_nework_data(self, version='latest'):
        path = posixpath.normpath(
            posixpath.join(version, 'network_data.json'))
        data = self._get_cache_data(path, decode=True)
        if data:
            return json.loads(data)

    def get_network_details(self):
        network_data = self._get_nework_data()
        if network_data:
            return self._parse_network_data(network_data)
        else:
            pass

    def _parse_network_data(self, network_data):
        if not network_data:
            return None
        LOG.debug(network_data)
        network_l2_config = self._parse_l2_network_data(network_data)
        LOG.debug(network_l2_config)
        network_l3_config = self._parse_l3_network_data(network_data, network_l2_config)
        LOG.debug(network_l3_config)
        network_l4_config = self._parse_l4_network_data(network_data)
        LOG.debug(network_l4_config)
        return base.AdvancedNetworkDetails(network_l2_config, network_l3_config, network_l4_config)

    def _parse_l2_network_data(self, network_data):
        if not network_data:
            return None
        parsed_links = []
        for link in network_data['config']:
            if link.get('type') in ['nameserver']:
                continue
            parsed_link = {
                'name': None,
                'type': None,
                'meta_type': None,
                'mac_address': None,
                'mtu': None
            }
            if link.get('id'):
                parsed_link['name'] = link['id']
            if link.get('type'):
                parsed_link['meta_type'] = link['type']
                parsed_link['type'] = 'phy'
                if link['type'] in ['ovs', 'vif']:
                    parsed_link['type'] = 'phy'
                elif link['type'] in ['phy', 'bond', 'vlan']:
                    parsed_link['type'] = link['type']
            if link.get('mtu'):
                parsed_link['mtu'] = link['mtu']
            if link.get('mac_address'):
                parsed_link['mac_address'] = link['mac_address'].upper()
            parsed_links.append(parsed_link)
        return parsed_links

    def _parse_l3_network_data(self, network_data, network_l2_config):
        if not (network_data and network_data['config']):
            return None
        parsed_networks = []
        for network_config in network_data['config']:
            if network_config.get('subnets'):
                for subnet in network_config.get('subnets'):
                    parsed_network = {
                        'mac_address': None,
                        'ip_address': None,
                        'prefix': None,
                        'gateway': None,
                        'type': None
                    }
                    parsed_network['mac_address'] = network_config.get('mac_address')
                    parsed_network['gateway'] = subnet.get('gateway')
                    if subnet.get('address'):
                        parsed_network['prefix'] = subnet.get('address').split('/')[1]
                        parsed_network['ip_address'] = subnet.get('address').split('/')[0]
                        version = netaddr.IPAddress(subnet.get('address')).version
                        if version == 4:
                            parsed_network['type'] = 'ipv4'
                        elif version == 6:
                            parsed_network['type'] = 'ipv6'

                    parsed_networks.append(parsed_network)
        return parsed_networks

    def _parse_l4_network_data(self, network_data):
        if not (network_data and network_data['config']):
            return None
        parsed_dnsses = []
        for service in network_data['config']:
            if service['type'] == 'nameserver':
                parsed_dnsses.append(service['address'])
        return {'dns_config': parsed_dnsses}
