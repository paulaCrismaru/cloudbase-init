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

import unittest

try:
    import unittest.mock as mock
except ImportError:
    import mock

from cloudbaseinit.plugins.windows import createuser
from cloudbaseinit.tests import testutils


class CreateUserPluginTests(unittest.TestCase):

    def setUp(self):
        self._create_user = createuser.CreateUserPlugin()

    @mock.patch('cloudbaseinit.osutils')
    def test__create_user_logon(self, mock_osutils):
        mock_token = mock.sentinel.token
        mock_osutils.create_user_logon_session.return_value = mock_token

        self._create_user._create_user_logon(
            mock.sentinel.user_name,
            mock.sentinel.password,
            mock.sentinel.password_expires,
            mock_osutils)

        mock_osutils.create_user_logon_session.assert_called_once_with(
            mock.sentinel.user_name,
            mock.sentinel.password,
            mock.sentinel.password_expires)
        mock_osutils.close_user_logon_session.assert_called_once_with(
            mock_token)

    @mock.patch('cloudbaseinit.osutils')
    def test__create_user_logon_fails(self, mock_osutils):
        mock_osutils.create_user_logon_session.side_effect = Exception

        with testutils.LogSnatcher('cloudbaseinit.plugins.windows.'
                                   'createuser') as snatcher:
            self._create_user._create_user_logon(
                mock.sentinel.user_name,
                mock.sentinel.password,
                mock.sentinel.password_expires,
                mock_osutils)

        mock_osutils.create_user_logon_session.assert_called_once_with(
            mock.sentinel.user_name,
            mock.sentinel.password,
            mock.sentinel.password_expires)

        expected_logging = [
            "Cannot create a user logon session for user: \"%s\""
            % mock.sentinel.user_name
        ]
        with self.assertRaises(Exception):
            self.assertEqual(snatcher.output, expected_logging)
            self.assertFalse(mock_osutils.close_user_logon_session.called)
