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

import unittest

try:
    import unittest.mock as mock
except ImportError:
    import mock

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.plugins.common import base
from cloudbaseinit.plugins.common import createuser
from cloudbaseinit.tests import testutils
from cloudbaseinit.plugins.common import constants

CONF = cloudbaseinit_conf.CONF


class CreateUserPluginTests(unittest.TestCase):

    def setUp(self):
        self._create_user = createuser.BaseCreateUserPlugin()

    @testutils.ConfPatcher('username', 'fake_username')
    def test_get_username(self):
        fake_data = {
            constants.SHARED_DATA_USERNAME: None
        }
        result = self._create_user._get_username(fake_data)
        self.assertEqual('fake_username', result)
        self.assertEqual(fake_data[constants.SHARED_DATA_USERNAME], result)

    @testutils.ConfPatcher('groups', ['Group 1', 'Group 2'])
    def test_get_groups(self):
        expected_groups = ['Group 1', 'Group 2']
        result = self._create_user._get_groups({})
        self.assertEqual(result, expected_groups)

    def test_get_expire_status(self):
        fake_data = {}
        result = self._create_user._get_expire_status(fake_data)
        self.assertEqual(False, result)

    def test_get_user_activity(self):
        fake_data = {}
        result = self._create_user._get_user_activity(fake_data)
        self.assertEqual(False, result)

    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    def test_get_password(self, mock_get_os_utils):
        expected_password = "Password"
        fake_shared_data = {
            constants.SHARED_DATA_PASSWORD: None
        }
        mock_utils = mock.Mock()
        mock_utils.get_maximum_password_length.return_value = None
        mock_utils.generate_random_password.return_value = expected_password
        mock_get_os_utils.return_value = mock_utils

        result = self._create_user._get_password(fake_shared_data)
        self.assertEqual(expected_password, result)
        mock_utils.get_maximum_password_length.assert_called_once()
        mock_utils.generate_random_password.assert_called_once()
        self.assertEqual(expected_password, fake_shared_data[
                         constants.SHARED_DATA_PASSWORD])

    @mock.patch('cloudbaseinit.plugins.common.createuser.'
                'BaseCreateUserPlugin.load')
    @mock.patch('cloudbaseinit.plugins.common.createuser.'
                'BaseCreateUserPlugin.manage_user_data')
    def test_execute(self, mock_manage_user_data, mock_load):
        fake_service = "fake_service"
        fake_shared_data = "fake_shared_data"

        response = self._create_user.execute(fake_service, fake_shared_data)
        self.assertEqual((base.PLUGIN_EXECUTION_DONE, False), response)
        mock_manage_user_data.assert_called_once()
        mock_load.assert_called_once_with(fake_shared_data)
