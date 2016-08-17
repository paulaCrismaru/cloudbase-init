# Copyright 2013 Cloudbase Solutions Srl
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
import unittest

try:
    import unittest.mock as mock
except ImportError:
    import mock

from cloudbaseinit import exception
from cloudbaseinit.plugins.common import base
from cloudbaseinit.plugins.common.usermanagement \
    import *
from cloudbaseinit.tests import testutils


class FakeBaseUserManager(BaseUserManager):

    def _get_username(self, data):
        return "fake username"

    def _get_password(self, data):
        return "fake password"

    def _get_groups(self, data):
        return ["fake group 1", "fake group 2"]

    def _get_expire_status(self, data):
        return "fake expire"

    def _get_user_activity(self, data):
        return "fake activity"


@mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
class TestBaseUserManager(unittest.TestCase):

    def setUp(self):
        self._user_management = FakeBaseUserManager()
        self._user_management._username = self._user_management._get_username(
                                                                    "fake data")

    def test_manage_user_exists(self, mock_get_os_utils):
        mock_utils = mock.Mock()
        mock_utils.user_exists.return_value = True
        mock_utils.set_user_password.return_value = True
        mock_get_os_utils.return_value = mock_utils
        with testutils.LogSnatcher('cloudbaseinit.plugins.common.'
                                   'usermanagement') as snatcher:
            self._user_management.manage_user_data()

        expected_logging = ['Setting password for existing user "%s"'
                            % self._user_management._username]
        mock_utils.user_exists.assert_called_once_with(
            self._user_management._username)
        mock_utils.set_user_password.assert_called_once_with(
            self._user_management._username,
            self._user_management._password,
            self._user_management._expire_status)
        self.assertEqual(expected_logging, snatcher.output)

    def test_manage_user_creation(self, mock_get_os_utils):
        mock_utils = mock.Mock()
        mock_utils.user_exists.return_value = False
        mock_get_os_utils.return_value = mock_utils

        with testutils.LogSnatcher('cloudbaseinit.plugins.common.'
                                   'usermanagement') as snatcher:
            self._user_management.manage_user_data()
        expected_logging = ['Creating user "%s" and setting password'
                            % (self._user_management._username)]

        mock_utils.user_exists.assert_called_once_with(
            self._user_management._username)
        self.assertEqual(expected_logging, snatcher.output)

    @mock.patch("cloudbaseinit.plugins.common.usermanagement."
                "BaseUserManager.post_create_user")
    def test_no_user_activity(self, mock_post_create, mock_os_utils):
        self._user_management._user_activity = False
        self._user_management.manage_user_data()
        mock_post_create.assert_called_once()

    def test_add_user_to_group(self, mock_get_os_utils):
        mock_utils = mock.Mock()
        mock_utils.add_user_to_local_group.return_value = True
        mock_get_os_utils.return_value = mock_utils

        self._user_management._groups = ['fake group 1', 'fake group 2']
        self._user_management.manage_user_data()
        self.assertEqual(mock_utils.add_user_to_local_group.call_count, 2)

    def test_add_user_to_group_exception(self, mock_get_os_utils):
        mock_utils = mock.Mock()
        e = Exception("fake exception")
        mock_utils.add_user_to_local_group.side_effect = e
        mock_utils.user_exists.return_value = True
        mock_get_os_utils.return_value = mock_utils

        self._user_management._groups = ['fake group 1', 'fake group 2']
        with testutils.LogSnatcher('cloudbaseinit.plugins.common.'
                                   'usermanagement') as snatcher:
            self._user_management.manage_user_data()

        expected_logging = [
            'Setting password for existing user "{0}"'.format(
                self._user_management._username),
            'Cannot add user to group "fake group 1"',
            'Cannot add user to group "fake group 2"'
        ]
        with self.assertRaises(Exception):
            self.assertEqual(expected_logging, snatcher.output)
            self.assertEqual(mock_utils.add_user_to_local_group.call_count, 3)

    def test_load(self, _):
        data = "fake_data"
        self._user_management.load(data)


class FakeBaseUserSSHPublicKeysManager(BaseUserSSHPublicKeysManager):
    def _get_username(self, data=None):
        pass

    def _get_ssh_public_keys(self, data=None):
        pass


@mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
class TestBaseUserSSHPublicKeysManager(unittest.TestCase):

    def setUp(self):
        self._base_user_ssh = FakeBaseUserSSHPublicKeysManager()

    def test_manage_user_no_ssh_keys(self, _):
        self._base_user_ssh._ssh_keys = False

        with testutils.LogSnatcher('cloudbaseinit.plugins.common.'
                                   'usermanagement') as snatcher:
            self._base_user_ssh.manage_user_ssh_keys()

        expected_logging = ['Public keys not found!']
        self.assertEqual(snatcher.output, expected_logging)

    def test_manage_user_not_home(self, mock_get_os_utils):
        self._base_user_ssh._ssh_keys = "fake key"
        mock_utils = mock.Mock()
        mock_utils.get_user_home.return_value = None
        mock_get_os_utils.return_value = mock_utils
        self.assertRaises(exception.CloudbaseInitException,
                          self._base_user_ssh.manage_user_ssh_keys)
        mock_utils.get_user_home.assert_called_once()

    @mock.patch("os.path")
    @mock.patch("os.makedirs")
    def _test_manage_user_ssh_keys(self, mock_os_makedirs, mock_os_path,
                                   mock_get_os_utils, os_path_exists):
        self._base_user_ssh._ssh_keys = "fake_ssh_key"
        self._base_user_ssh._username = "fake_username"

        mock_utils = mock.Mock()
        mock_utils.get_os_utils.return_value = True
        mock_utils.get_user_home.return_value = self._base_user_ssh._username
        mock_get_os_utils.return_value = mock_utils

        mock_os_path.exists.return_value = False
        mock_os_path.join.return_value = "fake_join"
        expected_logging = [
            "User home: %s" % self._base_user_ssh._username,
            "Writing SSH public keys in: %s" % "fake_join"
        ]
        with testutils.LogSnatcher('cloudbaseinit.plugins.common.'
                                   'usermanagement') as snatcher:
            with mock.patch('cloudbaseinit.plugins.common.usermanagement'
                            '.open',
                            mock.mock_open(), create=True):
                self._base_user_ssh.manage_user_ssh_keys()

        mock_utils.get_user_home.assert_called_once_with(
            self._base_user_ssh._username)
        if not os_path_exists:
            mock_os_makedirs.assert_called_once()
        self.assertEqual(mock_os_path.join.call_count, 2)
        self.assertEqual(snatcher.output, expected_logging)

    def test_manage_user_ssh_keys_path_exists(self, mock_get_os_utils):
        self._test_manage_user_ssh_keys(mock_get_os_utils,
                                        os_path_exists=True)

    @mock.patch("os.path")
    @mock.patch("os.makedirs")
    def test_manage_user_ssh_keys_path_no_exists(self, mock_os_makedirs,
                                                 mock_os_path,
                                                 mock_get_os_utils):
        self._test_manage_user_ssh_keys(mock_os_makedirs, mock_os_path,
                                        mock_get_os_utils,
                                        os_path_exists=False)

    def test_load(self, _):
        data = "fake_data"
        self._base_user_ssh.load(data)
