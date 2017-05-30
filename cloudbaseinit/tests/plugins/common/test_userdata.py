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
import pkgutil
import tempfile
import unittest

try:
    import unittest.mock as mock
except ImportError:
    import mock


from cloudbaseinit.metadata.services import base as metadata_services_base
from cloudbaseinit.plugins.common import base
from cloudbaseinit.plugins.common import userdata
from cloudbaseinit.tests.metadata import fake_json_response
from cloudbaseinit.tests import testutils


class FakeService(object):
    def __init__(self, user_data):
        self.user_data = user_data

    def get_decoded_user_data(self):
        return self.user_data


def _create_tempfile():
    fd, tmp = tempfile.mkstemp()
    os.close(fd)
    return tmp


class UserDataPluginTest(unittest.TestCase):

    def setUp(self):
        self._userdata = userdata.UserDataPlugin()
        self.fake_data = fake_json_response.get_fake_metadata_json(
            '2013-04-04')

    @mock.patch('cloudbaseinit.plugins.common.basedataplugin.'
                'BaseUserdataPlugin._process_data')
    def _test_execute(self, mock_process_data, ret_val):
        mock_service = mock.MagicMock()
        mock_service.get_decoded_user_data.side_effect = [ret_val]

        response = self._userdata.execute(service=mock_service,
                                          shared_data=None)

        mock_service.get_decoded_user_data.assert_called_once_with()
        if ret_val is metadata_services_base.NotExistingMetadataException:
            self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))
        elif ret_val is None:
            self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_execute(self):
        self._test_execute(ret_val='fake_data')

    def test_execute_no_data(self):
        self._test_execute(ret_val=None)

    def test_execute_NotExistingMetadataException(self):
        self._test_execute(
            ret_val=metadata_services_base.NotExistingMetadataException)


class TestCloudConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin = userdata.UserDataPlugin()
        cls.userdata = pkgutil.get_data('cloudbaseinit.tests.resources',
                                        'cloud_config_userdata').decode()

    def create_tempfiles(self, number):
        for _ in range(number):
            tmp = _create_tempfile()
            self.addCleanup(os.remove, tmp)
            yield tmp

    def test_cloud_config_multipart(self):
        b64, b64_binary, gz, gz_binary = list(self.create_tempfiles(4))

        service = FakeService(self.userdata.format(b64=b64,
                                                   b64_binary=b64_binary,
                                                   gzip=gz,
                                                   gzip_binary=gz_binary))
        with testutils.LogSnatcher('cloudbaseinit.plugins.'
                                   'common.userdataplugins.'
                                   'cloudconfigplugins') as snatcher:
            status, reboot = self.plugin.execute(service, {})

        for path in (b64, b64_binary, gz, gz_binary):
            self.assertTrue(os.path.exists(path),
                            "Path {} should exist.".format(path))
            with open(path) as stream:
                self.assertEqual('42', stream.read())

        self.assertEqual(status, 1)
        self.assertFalse(reboot)
        expected_logging = [
            'Unknown encoding, doing nothing.',
            'Fail to process permissions None, assuming 420',
            'Fail to process permissions None, assuming 420',
            'Fail to process permissions None, assuming 420'
        ]
        self.assertEqual(expected_logging, snatcher.output)
