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

from oslo_log import log as oslo_logging

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.metadata.services import base

CONF = cloudbaseinit_conf.CONF
LOG = oslo_logging.getLogger(__name__)


class DigitalOceanService(base.BaseHTTPMetadataService):

    _metadata_version = 'v1'

    def __init__(self):
        super(DigitalOceanService, self).__init__(
            base_url=CONF.digitalocean.metadata_base_url,
            https_allow_insecure=CONF.digitalocean.https_allow_insecure,
            https_ca_bundle=CONF.digitalocean.https_ca_bundle)
        self._enable_retry = True

    def load(self):
        super(DigitalOceanService, self).load()
        LOG.debug('Loading DigitalOcean Service')
        try:
            self.get_host_name()
            return True
        except Exception as ex:
            LOG.exception(ex)
            LOG.debug('Metadata not found at URL \'%s\'' %
                      CONF.digitalocean.metadata_base_url)
            return False

    def get_host_name(self):
        return self._get_meta_data().get("hostname")

    def _get_meta_data(self, version='v1'):
        data = self._get_cache_data('metadata/%s.json' %
                                    version, decode=True)
        if data:
            return json.loads(data)

    def get_instance_id(self):
        return str(self._get_meta_data().get("droplet_id"))

    def get_public_keys(self):
        public_keys = self._get_meta_data().get("public_keys", [])
        return list(set((key.strip() for key in public_keys)))

    def get_user_data(self):
        return self._get_cache_data('metadata/%s/user-data' %
                                    self._metadata_version, decode=True)

    def get_vendor_data(self):
        return self._get_cache_data('metadata/%s/vendor-data' %
                                    self._metadata_version, decode=True)
