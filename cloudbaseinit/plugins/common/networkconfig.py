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


import re

from oslo_log import log as oslo_logging

from cloudbaseinit import exception
from cloudbaseinit.metadata.services import base as service_base
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins.common import base as plugin_base
from cloudbaseinit.utils import network


LOG = oslo_logging.getLogger(__name__)

class NetworkConfigPlugin(plugin_base.BasePlugin):

    def execute(self, service, shared_data):
        osutils = osutils_factory.get_os_utils()
        network_details = service.get_network_details()
        if not network_details:
            return plugin_base.PLUGIN_EXECUTION_DONE, False
        reboot_required = False
        if network_details.network_l2_config:
            reboot_required = osutils.configure_l2_networking(network_details.network_l2_config)
        if network_details.network_l3_config:
            reboot_required = osutils.configure_l3_networking(network_details.network_l3_config) or reboot_required
        if network_details.network_l4_config:
            reboot_required = osutils.configure_l4_networking(network_details.network_l4_config) or reboot_required
        return plugin_base.PLUGIN_EXECUTION_DONE, reboot_required
