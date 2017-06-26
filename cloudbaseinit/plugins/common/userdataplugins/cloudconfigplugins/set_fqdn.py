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

from oslo_log import log as oslo_logging

from cloudbaseinit.plugins.common.userdataplugins.cloudconfigplugins import (
    set_hostname
)


LOG = oslo_logging.getLogger(__name__)


class SetFQDNPlugin(set_hostname.SetHostnamePlugin):
    """Setting the FQDN for the underlying platform.

    If the FQDN is changed a restart will be required.

    """
    _keys = ["fqdn"]
    _target = "FQDN"

    def conflicts(self, part):
        return part.get('preserve_hostname')
