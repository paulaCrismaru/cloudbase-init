# Copyright 2015 Cloudbase Solutions Srl
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

from oslo_log import log as oslo_logging

from cloudbaseinit.osutils import factory
from cloudbaseinit.plugins.common.userdataplugins.cloudconfigplugins import (
    base
)
from cloudbaseinit.utils import hostname


LOG = oslo_logging.getLogger(__name__)


class SetHostnamePlugin(base.BaseCloudConfigPlugin):
    """Change the hostname for the underlying platform.

    If the hostname is changed a restart will be required.

    To change the hostname to 'myhostname', use this syntax:

        hostname: myhostname

    """

    _keys = ["hostname", "set_hostname"]

    def _execute(self, part, service=None):
        reboot_required = False
        plugin_key = self._get_used_key(part)
        data = part.get(plugin_key)
        if not self._conflicts(part):
            LOG.info("Changing %(target)s to %(data)s",
                     {"target": self.keys[0], "data": data})
            osutils = factory.get_os_utils()
            _, reboot_required = hostname.set_hostname(osutils, data)
        else:
            LOG.warning("Plugin %s will not be executed due to its lower "
                        "priority compared to the other given plugins",
                        plugin_key)
        return reboot_required

    def _conflicts(self, part):
        return part.get("preserve_hostname") or part.get("fqdn")
