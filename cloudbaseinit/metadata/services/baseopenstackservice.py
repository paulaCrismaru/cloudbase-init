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

    def _parse_legacy_network_data(self, legacy_network_data):
        if not legacy_network_data:
            return
        parsed_links = []
        parsed_networks = []
        for iface in legacy_network_data:
            parsed_link = base.L2NetworkDetails.copy()
            parsed_network_ipv4 = base.L3NetworkDetails.copy()
            parsed_network_ipv6 = base.L3NetworkDetails.copy()

            parsed_link['id'] = iface.get('name')
            parsed_link['name'] = iface.get('name')
            parsed_link['mac_address'] = iface.get('mac')

            parsed_network_ipv4['ip_address'] = iface.get('address')
            parsed_network_ipv4['netmask'] = iface.get('netmask')
            parsed_network_ipv4['gateway'] = iface.get('gateway')
            parsed_network_ipv4['dns_nameservers'] = iface.get('dnsnameservers')

            parsed_network_ipv6['ip_address'] = iface.get('address6')
            parsed_network_ipv6['netmask'] = iface.get('netmask6')
            parsed_network_ipv6['gateway'] = iface.get('gateway6')
            parsed_links.append(parsed_link)
            parsed_networks.append(parsed_network_ipv4)
            parsed_networks.append(parsed_network_ipv6)

        return base.AdvancedNetworkDetails(parsed_links,
                                           parsed_networks,
                                           None)

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
