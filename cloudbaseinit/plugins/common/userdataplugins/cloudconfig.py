# Copyright 2013 Mirantis Inc.
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

from oslo_log import log as oslo_logging
import yaml

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.plugins.common import execcmd
from cloudbaseinit.plugins.common.userdataplugins import base
from cloudbaseinit.plugins.common.userdataplugins.cloudconfigplugins import (
    factory
)


CONF = cloudbaseinit_conf.CONF
LOG = oslo_logging.getLogger(__name__)
DEFAULT_ORDER_VALUE = 999


class CloudConfigError(Exception):
    pass


class CloudConfigPlugin(base.BaseUserDataPlugin):

    def __init__(self):
        super(CloudConfigPlugin, self).__init__("text/cloud-config")

    def process_non_multipart(self, part, service=None):
        """Process the given data, if it can be loaded through yaml.

        If any plugin requires a reboot, it will return a particular
        value, which will be processed on a higher level.
        """
        plugins = factory.load_plugins()
        content = None
        reboot = execcmd.NO_REBOOT
        try:
            content = self.from_yaml(part)
        except CloudConfigError as ex:
            LOG.error('Could not process part type %(type)r: %(err)r',
                      {'type': type(part), 'err': str(ex)})
        else:
            for plugin in plugins:
                try:
                    requires_reboot = plugin.execute(content, service)
                    if requires_reboot:
                        reboot = execcmd.RET_END
                except Exception:
                    plugin_name = plugin._get_used_key(content)
                    LOG.exception("Processing plugin %s failed", plugin_name)
        return reboot

    def process(self, part, service=None):
        payload = part.get_payload(decode=True)
        return self.process_non_multipart(payload, service)

    @classmethod
    def from_yaml(cls, stream):
        loader = getattr(yaml, 'CLoader', yaml.Loader)
        try:
            content = yaml.load(stream, Loader=loader)
        except (TypeError, ValueError, AttributeError):
            raise CloudConfigError("Invalid yaml stream provided.")
        if not content:
            raise CloudConfigError("Empty yaml stream provided.")
        return content
