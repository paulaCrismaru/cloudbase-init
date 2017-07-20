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

from cloudbaseinit.plugins.common import base as plugin_base
from cloudbaseinit.plugins.common import networkconfig


class TestNetworkConfigPlugin(unittest.TestCase):

    def setUp(self):
        self._network_plugin = networkconfig.NetworkConfigPlugin()

    @mock.patch("cloudbaseinit.osutils.factory.get_os_utils")
    def _test_execute(self, mock_get_os_utils, network_details):
        mock_service = mock.Mock()
        osutils = mock_get_os_utils()
        osutils.configure_l2_networking.return_value = True
        osutils.configure_l3_networking.return_value = True
        osutils.configure_l4_networking.return_value = True
        mock_service.get_network_details.return_value = network_details

        result = self._network_plugin.execute(mock_service, None)

        reboot_required = True
        if not network_details:
            reboot_required = False
        else:
            if network_details.network_l2_config:
                osutils.configure_l2_networking.assert_called_once_with(
                    network_details.network_l2_config)
            if network_details.network_l3_config:
                osutils.configure_l3_networking.assert_called_once_with(
                    network_details.network_l3_config)
            if network_details.network_l4_config:
                osutils.configure_l4_networking.assert_called_once_with(
                    network_details.network_l4_config)
        self.assertEqual(result, (plugin_base.PLUGIN_EXECUTION_DONE,
                                  reboot_required))

    def test_execute_no_network_data(self):
        self._test_execute(network_details=None)

    def test_execute(self):
        network_details = mock.Mock()
        network_details.network_l2_config = "fake l2 data"
        network_details.network_l3_config = "fake l3 data"
        network_details.network_l4_config = "fake l4 data"
        self._test_execute(network_details=network_details)
