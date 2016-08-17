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

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins.common import base
from cloudbaseinit.plugins.common import constants
from cloudbaseinit.plugins.common import usermanagement


CONF = cloudbaseinit_conf.CONF


class BaseCreateUserPlugin(base.BasePlugin, usermanagement.BaseUserManager):
    """This is a base class for creating or modifying an user."""

    def _get_username(self, data):
        user_name = CONF.username
        data[constants.SHARED_DATA_USERNAME] = user_name
        return user_name

    def _get_groups(self, data):
        return CONF.groups

    def _get_expire_status(self, data):
        return False

    def _get_user_activity(self, data):
        return False

    def _get_password(self, data):
        # Generate a temporary random password to be replaced
        # by SetUserPasswordPlugin (starting from Grizzly)
        osutils = osutils_factory.get_os_utils()
        maximum_length = osutils.get_maximum_password_length()
        password = osutils.generate_random_password(maximum_length)
        # TODO(alexpilotti): encrypt with DPAPI
        data[constants.SHARED_DATA_PASSWORD] = password
        return password

    def execute(self, service, shared_data):
        self.load(shared_data)
        self.manage_user_data()
        return base.PLUGIN_EXECUTION_DONE, False
