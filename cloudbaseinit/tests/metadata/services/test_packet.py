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

import importlib
import requests
import unittest

try:
    import unittest.mock as mock
except ImportError:
    import mock

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.tests import testutils
from six.moves.urllib import error


CONF = cloudbaseinit_conf.CONF
BASE_MODULE_PATH = ("cloudbaseinit.metadata.services.base."
                    "BaseHTTPMetadataService")
MODULE_PATH = "cloudbaseinit.metadata.services.packet"


class PacketServiceTest(unittest.TestCase):

    def setUp(self):
        self._win32com_mock = mock.MagicMock()
        self._ctypes_mock = mock.MagicMock()
        self._ctypes_util_mock = mock.MagicMock()
        self._win32com_client_mock = mock.MagicMock()
        self._pywintypes_mock = mock.MagicMock()
        self._module_patcher = mock.patch.dict(
            'sys.modules',
            {'win32com': self._win32com_mock,
             'ctypes': self._ctypes_mock,
             'ctypes.util': self._ctypes_util_mock,
             'win32com.client': self._win32com_client_mock,
             'pywintypes': self._pywintypes_mock})
        self._module_patcher.start()
        self.addCleanup(self._module_patcher.stop)

        self._packet_module = importlib.import_module(MODULE_PATH)
        self._packet_service = self._packet_module.PacketService()
        self.snatcher = testutils.LogSnatcher(MODULE_PATH)

    def test_can_post_password(self):
        self.assertTrue(self._packet_service.can_post_password)

    @mock.patch(MODULE_PATH + ".PacketService._get_cache_data")
    def test_get_meta_data(self, mock_get_cache_data):
        mock_get_cache_data.return_value = '{"fake": "data"}'
        response = self._packet_service._get_meta_data()
        mock_get_cache_data.assert_called_with("metadata", decode=True)
        self.assertEqual({"fake": "data"}, response)

    @mock.patch(BASE_MODULE_PATH + ".load")
    @mock.patch(MODULE_PATH + ".PacketService._get_cache_data")
    def test_load(self, mock_get_cache_data, mock_load):
        mock_get_cache_data.return_value = '{"fake": "data"}'
        self.assertTrue(self._packet_service.load())

    @mock.patch(BASE_MODULE_PATH + ".load")
    @mock.patch(MODULE_PATH + ".PacketService._get_cache_data")
    def test_load_fails(self, mock_get_cache_data, mock_load):
        with testutils.LogSnatcher(MODULE_PATH) as snatcher:
            self.assertFalse(self._packet_service.load())
        self.assertEqual(snatcher.output,
                         ['Metadata not found at URL \'%s\'' %
                          CONF.packet.metadata_base_url])

    @mock.patch(MODULE_PATH + ".PacketService._get_meta_data")
    def test_get_instance_id(self, mock_get_meta_data):
        response = self._packet_service.get_instance_id()
        mock_get_meta_data.assert_called_once_with()
        mock_get_meta_data().get.assert_called_once_with('id')
        self.assertEqual(mock_get_meta_data.return_value.get.return_value,
                         response)

    @mock.patch(MODULE_PATH +
                ".PacketService._get_meta_data")
    def test_get_host_name(self, mock_get_meta_data):
        response = self._packet_service.get_host_name()
        mock_get_meta_data.assert_called_once_with()
        mock_get_meta_data().get.assert_called_once_with('hostname')
        self.assertEqual(mock_get_meta_data.return_value.get.return_value,
                         response)

    @mock.patch(MODULE_PATH +
                ".PacketService._get_meta_data")
    def _test_get_public_keys(self, mock_get_meta_data, mock_exec_with_retry,
                              public_keys):
        mock_get_meta_data.return_value = {
            "ssh_keys": public_keys
        }
        response = self._packet_service.get_public_keys()
        mock_get_meta_data.assert_called_once_with()

        if public_keys:
            public_keys = list(set((key.strip() for key in public_keys)))
        else:
            public_keys = []

        self.assertEqual(sorted(public_keys),
                         sorted(response))

    def test_get_public_keys(self):
        self._test_get_public_keys(public_keys=["fake keys"] * 3)

    def test_get_public_keys_empty(self):
        self._test_get_public_keys(public_keys=None)

    @mock.patch(MODULE_PATH +
                ".PacketService._exec_with_retry")
    @mock.patch(MODULE_PATH +
                ".PacketService._get_meta_data")
    def _test_get_encryption_public_key(self, mock_get_meta_data,
                                        mock_exec_with_retry,
                                        request_error=None):
        path = 'fake path'
        mock_get_meta_data.return_value = {'phone_home_url': path}
        if request_error:
            mock_exec_with_retry.side_effect =  \
                requests.RequestException("fake reason")
        else:
            mock_exec_with_retry.return_value = "fake data"
        response = self._packet_service.get_encryption_public_key()
        if request_error:
            self.assertFalse(response)
        else:
            self.assertEqual(response, mock_exec_with_retry.return_value)
        mock_get_meta_data.assert_called_once_with()

    def test_get_encryption_public_key(self):
        self._test_get_encryption_public_key()

    def test_get_encryption_public_key_error(self):
        self._test_get_encryption_public_key(request_error=True)

    @mock.patch(MODULE_PATH +
                ".PacketService._get_cache_data")
    def test_get_user_data(self, mock_get_cache_data):
        response = self._packet_service.get_user_data()
        mock_get_cache_data.assert_called_once_with("userdata")
        self.assertEqual(mock_get_cache_data.return_value, response)

    @mock.patch(BASE_MODULE_PATH + "._http_request")
    def test_post_data(self, mock_http_request):
        path = "fake path"
        data = "fake data"
        self._packet_service._post_data(path, data)
        mock_http_request.assert_called_once_with(
            url=path, data=data, method="post")

    @mock.patch(MODULE_PATH +
                ".PacketService._exec_with_retry")
    @mock.patch(MODULE_PATH +
                ".PacketService._get_meta_data")
    def test_post_password(self, mock_get_meta_data, mock_exec_with_retry):
        response = self._packet_service.post_password(b"fake pasword")
        self.assertEqual(response, mock_exec_with_retry())
        mock_get_meta_data().get.assert_called_once_with('phone_home_url')

    @mock.patch(MODULE_PATH +
                ".PacketService._exec_with_retry")
    @mock.patch(MODULE_PATH +
                ".PacketService._get_meta_data")
    def test_post_password_fails(self, mock_get_meta_data,
                                 mock_exec_with_retry):
        ex = error.HTTPError(None, None, None, None, None)
        mock_exec_with_retry.side_effect = ex
        with self.assertRaises(error.HTTPError):
            with testutils.LogSnatcher(MODULE_PATH) as snatcher:
                self._packet_service.post_password(b"fake pasword")
        self.assertEqual(snatcher.output,
                         ["Failed to post password to the metadata service"])
        mock_get_meta_data().get.assert_called_once_with('phone_home_url')

    @mock.patch(MODULE_PATH +
                ".PacketService._post_data")
    @mock.patch(MODULE_PATH +
                ".PacketService._get_meta_data")
    def _test_call_home(self, mock_get_meta_data, mock_post_data,
                        expected_output, data):
        mock_get_meta_data.return_value = data
        with testutils.LogSnatcher(MODULE_PATH) as snatcher:
            self._packet_service._call_home()
        self.assertEqual(snatcher.output, expected_output)

    def test_call_home(self):
        expected_output = ["Calling home to: {0}".format("fake path")]
        self._test_call_home(expected_output=expected_output,
                             data={'phone_home_url': "fake path"})

    def test_call_home_fails(self):
        expected_output = ["Could not retrieve phone_home_url from metadata"]
        self._test_call_home(expected_output=expected_output, data={})

    @mock.patch(MODULE_PATH +
                ".PacketService._call_home")
    def test_provisioning_completed(self, mock_call_home):
        self._packet_service.provisioning_completed()
        mock_call_home.assert_called_once_with()

    @mock.patch(MODULE_PATH +
                ".PacketService._call_home")
    def test_provisioning_failed(self, mock_call_home):
        self._packet_service.provisioning_failed()
        mock_call_home.assert_called_once_with()
