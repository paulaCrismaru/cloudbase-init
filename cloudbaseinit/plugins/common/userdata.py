# Copyright 2012 Cloudbase Solutions Srl
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

import os

from oslo_log import log as oslo_logging

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.metadata.services import base as metadata_services_base
from cloudbaseinit.plugins.common import base
from cloudbaseinit.plugins.common import basedataplugin


CONF = cloudbaseinit_conf.CONF
LOG = oslo_logging.getLogger(__name__)


class UserDataPlugin(basedataplugin.BaseUserdataPlugin):

    def execute(self, service, shared_data):
        try:
            user_data = service.get_decoded_user_data()
        except metadata_services_base.NotExistingMetadataException:
            return base.PLUGIN_EXECUTION_DONE, False

        if not user_data:
            return base.PLUGIN_EXECUTION_DONE, False

        LOG.debug('User data content length: %d' % len(user_data))
        if CONF.userdata_save_path:
            user_data_path = os.path.abspath(
                os.path.expandvars(CONF.userdata_save_path))
            self._write_data(user_data, user_data_path)

        if CONF.process_userdata:
            return self._process_data(user_data)
        return base.PLUGIN_EXECUTION_DONE, False
