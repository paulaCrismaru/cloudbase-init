# Copyright 2016 Cloudbase Solutions Srl
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

import abc
import os

from oslo_log import log as oslo_logging
import six

from cloudbaseinit import exception
from cloudbaseinit.osutils import factory as osutils_factory


LOG = oslo_logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseUserSSHPublicKeysManager(object):

    def __init__(self):
        self._username = None
        self._ssh_keys = None

    @abc.abstractmethod
    def _get_username(self, data=None):
        pass

    @abc.abstractmethod
    def _get_ssh_public_keys(self, data=None):
        pass

    def load(self, data):
        self._username = self._get_username(data)
        self._ssh_keys = self._get_ssh_public_keys(data)

    def manage_user_ssh_keys(self):
        if not self._ssh_keys:
            LOG.debug('Public keys not found!')
            return
        osutils = osutils_factory.get_os_utils()
        user_home = osutils.get_user_home(self._username)
        if not user_home:
            raise exception.CloudbaseInitException("User profile not found!")

        LOG.debug("User home: %s" % user_home)
        user_ssh_dir = os.path.join(user_home, '.ssh')
        if not os.path.exists(user_ssh_dir):
            os.makedirs(user_ssh_dir)
        authorized_keys_path = os.path.join(user_ssh_dir, "authorized_keys")
        LOG.info("Writing SSH public keys in: %s" % authorized_keys_path)
        with open(authorized_keys_path, 'w') as file_handler:
            for public_key in self._ssh_keys:
                # All public keys are space-stripped.
                file_handler.write(public_key + "\n")


@six.add_metaclass(abc.ABCMeta)
class BaseUserManager(object):

    def __init__(self):
        self._username = None
        self._password = None
        self._expire_status = False
        self._groups = []
        self._user_activity = False

    @abc.abstractmethod
    def _get_username(self, data):
        pass

    @abc.abstractmethod
    def _get_password(self, data):
        pass

    @abc.abstractmethod
    def _get_groups(self, data):
        pass

    @abc.abstractmethod
    def _get_expire_status(self, data):
        pass

    @abc.abstractmethod
    def _get_user_activity(self, data):
        pass

    def load(self, data):
        self._username = self._get_username(data)
        self._password = self._get_password(data)
        self._expire_status = self._get_expire_status(data)
        self._groups = self._get_groups(data)
        self._user_activity = self._get_user_activity(data)

    def create_user(self, username, password, password_expires, osutils):
        osutils.create_user(username, password, password_expires)

    def post_create_user(self, user_name, password, password_expires, osutils):
        self._create_user_logon(user_name, password, password_expires, osutils)

    def _create_user_logon(self, user_name, password, password_expires, osutils):
        pass

    def manage_user_data(self):
        osutils = osutils_factory.get_os_utils()
        if osutils.user_exists(self._username):
            LOG.info('Setting password for existing user "%s"', self._username)
            osutils.set_user_password(self._username, self._password,
                                      self._expire_status)
        else:
            LOG.info('Creating user "%s" and setting password', self._username)
            self.create_user(self._username, self._password,
                             self._expire_status, osutils)

        if not self._user_activity:
            self.post_create_user(self._username, self._password,
                                  self._expire_status, osutils)

        for group_name in self._groups:
            try:
                osutils.add_user_to_local_group(self._username, group_name)
            except Exception:
                LOG.exception('Cannot add user to group "%s"', group_name)


class UserManager(BaseUserManager, BaseUserSSHPublicKeysManager):

    def __init__(self):
        super(BaseUserManager, self).__init__()
        self._ssh_keys = None

    def load(self, data):
        BaseUserManager.load(self, data)
        BaseUserSSHPublicKeysManager.load(self, data)
