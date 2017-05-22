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
import tempfile
import textwrap
import unittest

try:
    import unittest.mock as mock
except ImportError:
    import mock

from cloudbaseinit import exception
from cloudbaseinit.plugins.common import base
from cloudbaseinit.plugins.common import basedataplugin
from cloudbaseinit.tests.metadata import fake_json_response
from cloudbaseinit.tests import testutils


class FakeService(object):
    def __init__(self, user_data):
        self.user_data = user_data

    def get_decoded_user_data(self):
        return self.user_data.encode()


def _create_tempfile():
    fd, tmp = tempfile.mkstemp()
    os.close(fd)
    return tmp


class UserDataPluginTest(unittest.TestCase):

    def setUp(self):
        self._data = basedataplugin.BaseUserdataPlugin()
        self.fake_data = fake_json_response.get_fake_metadata_json(
            '2013-04-04')

    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    @mock.patch('os.unlink')
    @mock.patch('os.path.isdir')
    @mock.patch('os.makedirs')
    @mock.patch('os.path.dirname')
    @mock.patch('os.path.exists')
    def _test_write_data(self, mock_exists, mock_dirname, mock_makedirs,
                         mock_is_dir, mock_unlink, mock_get_os_utils,
                         os_exists_effects=None, is_dir=True):
        mock_data = str(mock.sentinel.data)
        mock_data_path = str(mock.sentinel.data_path)
        mock_osutils = mock.Mock()
        mock_get_os_utils.return_value = mock_osutils
        mock_exists.side_effect = os_exists_effects
        mock_is_dir.return_value = is_dir
        expected_logs = ["Writing userdata to: %s" % mock_data_path]
        if not is_dir:
            self.assertRaises(
                exception.CloudbaseInitException,
                self._data._write_data,
                mock_data, mock_data_path)
            return
        with mock.patch('cloudbaseinit.plugins.common.basedataplugin'
                        '.open', create=True):
            with testutils.LogSnatcher('cloudbaseinit.plugins.common.'
                                       'basedataplugin') as snatcher:
                self._data._write_data(mock_data, mock_data_path)
        self.assertEqual(snatcher.output, expected_logs)

    def test_write_userdata_fail(self):
        self._test_write_data(is_dir=False)

    def test_write_userdata(self):
        self._test_write_data(os_exists_effects=(False, True))

    @mock.patch('email.message_from_string')
    @mock.patch('cloudbaseinit.utils.encoding.get_as_string')
    def test_parse_mime(self, mock_get_as_string,
                        mock_message_from_string):
        fake_data = textwrap.dedent('''
        -----BEGIN CERTIFICATE-----
        MIIDGTCCAgGgAwIBAgIJAN5fj7R5dNrMMA0GCSqGSIb3DQEBCwUAMCExHzAdBgNV
        BAMTFmNsb3VkYmFzZS1pbml0LWV4YW1wbGUwHhcNMTUwNDA4MTIyNDI1WhcNMjUw
        ''')
        expected_logging = ['Data content:\n%s' % fake_data]
        mock_get_as_string.return_value = fake_data

        with testutils.LogSnatcher('cloudbaseinit.plugins.common.'
                                   'basedataplugin') as snatcher:
            response = self._data._parse_mime(data=fake_data)

        mock_get_as_string.assert_called_once_with(fake_data)
        mock_message_from_string.assert_called_once_with(
            mock_get_as_string.return_value)
        self.assertEqual(response, mock_message_from_string().walk())
        self.assertEqual(expected_logging, snatcher.output)

    def test_get_header(self):
        fake_data = "fake-data"
        self.assertEqual(fake_data, self._data._get_headers(fake_data))
        fake_data = None
        with self.assertRaises(exception.CloudbaseInitException):
            self._data._get_headers(fake_data)

    @mock.patch('cloudbaseinit.plugins.common.userdataplugins.factory.'
                'load_plugins')
    @mock.patch('cloudbaseinit.plugins.common.basedataplugin.'
                'BaseUserdataPlugin._parse_mime')
    @mock.patch('cloudbaseinit.plugins.common.basedataplugin.'
                'BaseUserdataPlugin._process_part')
    @mock.patch('cloudbaseinit.plugins.common.basedataplugin.'
                'BaseUserdataPlugin._end_part_process_event')
    @mock.patch('cloudbaseinit.plugins.common.basedataplugin.'
                'BaseUserdataPlugin._process_non_multi_part')
    def _test_process_data(self, mock_process_non_multi_part,
                           mock_end_part_process_event,
                           mock_process_part, mock_parse_mime,
                           mock_load_plugins, data, reboot):
        mock_part = mock.MagicMock()
        mock_parse_mime.return_value = [mock_part]
        mock_process_part.return_value = (base.PLUGIN_EXECUTION_DONE, reboot)

        response = self._data._process_data(data=data)

        if data.startswith(b'Content-Type: multipart'):
            mock_load_plugins.assert_called_once_with()
            mock_parse_mime.assert_called_once_with(data)
            mock_process_part.assert_called_once_with(mock_part,
                                                      mock_load_plugins(), {})
            self.assertEqual((base.PLUGIN_EXECUTION_DONE, reboot), response)
        else:
            mock_process_non_multi_part.assert_called_once_with(data)
            self.assertEqual(mock_process_non_multi_part.return_value,
                             response)

    def test_process_data_multipart_reboot_true(self):
        self._test_process_data(data='Content-Type: multipart',
                                reboot=True)

    def test_process_data_multipart_reboot_false(self):
        self._test_process_data(data=b'Content-Type: multipart',
                                reboot=False)

    def test_process_data_non_multipart(self):
        self._test_process_data(data=b'Content-Type: non-multipart',
                                reboot=False)

    @mock.patch('cloudbaseinit.plugins.common.basedataplugin.'
                'BaseUserdataPlugin._add_part_handlers')
    @mock.patch('cloudbaseinit.plugins.common.execcmd'
                '.get_plugin_return_value')
    def _test_process_part(self, mock_get_plugin_return_value,
                           mock_add_part_handlers,
                           handler_func, data_plugin, content_type):
        mock_part = mock.MagicMock()
        mock_data_plugins = mock.MagicMock()
        mock_handlers = mock.MagicMock()
        mock_handlers.get.side_effect = [handler_func]
        mock_data_plugins.get.side_effect = [data_plugin]
        if content_type:
            _content_type = self._data._PART_HANDLER_CONTENT_TYPE
            mock_part.get_content_type.return_value = _content_type
        else:
            _content_type = 'other content type'
            mock_part.get_content_type.return_value = _content_type

        response = self._data._process_part(
            part=mock_part, data_plugins=mock_data_plugins,
            handlers=mock_handlers)
        mock_part.get_content_type.assert_called_once_with()
        mock_handlers.get.assert_called_once_with(
            _content_type)
        if handler_func:
            handler_func.assert_called_once_with(None, _content_type,
                                                 mock_part.get_filename(),
                                                 mock_part.get_payload())

            self.assertEqual(1, mock_part.get_content_type.call_count)
            self.assertEqual(2, mock_part.get_filename.call_count)
        else:
            mock_data_plugins.get.assert_called_once_with(_content_type)
            if data_plugin and content_type:
                data_plugin.process.assert_called_with(mock_part)
                mock_add_part_handlers.assert_called_with(
                    mock_data_plugins, mock_handlers,
                    data_plugin.process())
            elif data_plugin and not content_type:
                mock_get_plugin_return_value.assert_called_once_with(
                    data_plugin.process())
                self.assertEqual(mock_get_plugin_return_value.return_value,
                                 response)

    def test_process_part(self):
        handler_func = mock.MagicMock()
        self._test_process_part(handler_func=handler_func,
                                data_plugin=None, content_type=False)

    def test_process_part_no_handler_func(self):
        data_plugin = mock.MagicMock()
        self._test_process_part(handler_func=None,
                                data_plugin=data_plugin,
                                content_type=True)

    def test_process_part_not_content_type(self):
        data_plugin = mock.MagicMock()
        self._test_process_part(handler_func=None,
                                data_plugin=data_plugin,
                                content_type=False)
        self._test_process_part(handler_func=None,
                                data_plugin=None,
                                content_type=False)

    def test_process_part_exception_occurs(self):
        mock_part = mock_handlers = mock.MagicMock()
        mock_handlers.get.side_effect = Exception
        mock_part.get_content_type().side_effect = Exception
        self.assertEqual((1, False),
                         self._data._process_part(
                         part=mock_part,
                         data_plugins=None,
                         handlers=mock_handlers))

    @mock.patch('cloudbaseinit.plugins.common.basedataplugin.'
                'BaseUserdataPlugin._begin_part_process_event')
    def _test_add_part_handlers(self, mock_begin_part_process_event, ret_val):
        mock_data_plugins = mock.MagicMock(spec=dict)
        mock_new_handlers = mock.MagicMock(spec=dict)
        mock_handlers = mock.MagicMock(spec=dict)
        mock_handler_func = mock.MagicMock()

        mock_new_handlers.items.return_value = [('fake content type',
                                                 mock_handler_func)]
        if ret_val:
            mock_data_plugins.get.return_value = mock_handler_func
        else:
            mock_data_plugins.get.return_value = None

        self._data._add_part_handlers(
            data_plugins=mock_data_plugins,
            handlers=mock_handlers,
            new_handlers=mock_new_handlers)
        mock_data_plugins.get.assert_called_with('fake content type')
        if ret_val is None:
            mock_handlers.__setitem__.assert_called_once_with(
                'fake content type', mock_handler_func)
            mock_begin_part_process_event.assert_called_with(mock_handler_func)

    def test_add_part_handlers(self):
        self._test_add_part_handlers(ret_val=None)

    def test_add_part_handlers_skip_part_handler(self):
        mock_func = mock.MagicMock()
        self._test_add_part_handlers(ret_val=mock_func)

    def test_begin_part_process_event(self):
        mock_handler_func = mock.MagicMock()
        self._data._begin_part_process_event(
            handler_func=mock_handler_func)
        mock_handler_func.assert_called_once_with(None, "__begin__", None,
                                                  None)

    def test_end_part_process_event(self):
        mock_handler_func = mock.MagicMock()
        self._data._end_part_process_event(
            handler_func=mock_handler_func)
        mock_handler_func.assert_called_once_with(None, "__end__", None,
                                                  None)

    @mock.patch('cloudbaseinit.plugins.common.userdatautils'
                '.execute_user_data_script')
    def test_process_non_multi_part(self, mock_execute_data_script):
        data = b'fake'
        status, reboot = self._data._process_non_multi_part(data=data)
        mock_execute_data_script.assert_called_once_with(data.encode())
        self.assertEqual(status, 1)
        self.assertFalse(reboot)

    @mock.patch('cloudbaseinit.plugins.common.userdatautils'
                '.execute_user_data_script')
    def test_process_non_multipart_dont_process_x509(
            self, mock_execute_data_script):
        data = textwrap.dedent('''
        -----BEGIN CERTIFICATE-----
        MIIC9zCCAd8CAgPoMA0GCSqGSIb3DQEBBQUAMBsxGTAXBgNVBAMUEHVidW50dUBs
        b2NhbGhvc3QwHhcNMTUwNjE1MTAyODUxWhcNMjUwNjEyMTAyODUxWjAbMRkwFwYD
        -----END CERTIFICATE-----
        ''').encode()
        with testutils.LogSnatcher('cloudbaseinit.plugins.'
                                   'common.basedataplugin') as snatcher:
            status, reboot = self._data._process_non_multi_part(data=data)

        expected_logging = ['Found X509 certificate in userdata']
        self.assertFalse(mock_execute_data_script.called)
        self.assertEqual(expected_logging, snatcher.output)
        self.assertEqual(1, status)
        self.assertFalse(reboot)

    @mock.patch('cloudbaseinit.plugins.common.userdataplugins.factory.'
                'load_plugins')
    def test_process_non_multi_part_cloud_config(self, mock_load_plugins):
        data = b'#cloud-config'
        mock_return_value = mock.sentinel.return_value
        mock_cloud_config_plugin = mock.Mock()
        mock_cloud_config_plugin.process.return_value = mock_return_value
        mock_load_plugins.return_value = {
            'text/cloud-config': mock_cloud_config_plugin}
        status, reboot = self._data._process_non_multi_part(data=data)

        mock_load_plugins.assert_called_once_with()
        (mock_cloud_config_plugin
         .process_non_multipart.assert_called_once_with(data))
        self.assertEqual(status, 1)
        self.assertFalse(reboot)
