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
from cloudbaseinit.plugins.common import sshpublickeys
from cloudbaseinit.tests import testutils

CONF = cloudbaseinit_conf.CONF


class SetUserSSHPublicKeysPluginTests(unittest.TestCase):

    def setUp(self):
        self._set_ssh_keys_plugin = sshpublickeys.SetUserSSHPublicKeysPlugin()

    @testutils.ConfPatcher('username', 'fake_username')
    @mock.patch('cloudbaseinit.plugins.common.sshpublickeys.'
                'SetUserSSHPublicKeysPlugin.load')
    @mock.patch('cloudbaseinit.plugins.common.sshpublickeys.'
                'SetUserSSHPublicKeysPlugin.manage_user_ssh_keys')
    def test_execute(self, mock_manage_user_ssh, mock_load):
        fake_shared_data = "fake_shared_data"
        fake_service = "fake_service"
        response = self._set_ssh_keys_plugin.execute(fake_service,
                                                     fake_shared_data)
        mock_manage_user_ssh.assert_called_once()
        mock_load.assert_called_once_with(fake_service)
        self.assertEqual((base.PLUGIN_EXECUTION_DONE, False), response)

    @testutils.ConfPatcher('username', "fake_username")
    def test_get_username(self):
        data = "fake_data"
        result = self._set_ssh_keys_plugin._get_username(data)
        self.assertEqual(result, CONF.username)

    def test_get_ssh_public_keys(self):
        mock_data = mock.Mock()
        mock_data.get_public_keys.return_value = "fake_keys"

        result = self._set_ssh_keys_plugin._get_ssh_public_keys(mock_data)
        self.assertEqual(result, "fake_keys")
        mock_data.get_public_keys.assert_called_once()
