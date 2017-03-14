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

try:
    import unittest.mock as mock
except ImportError:
    import mock

from cloudbaseinit.tests import testutils


class TestAzureInstrumentation(testutils.CloudbaseInitTestBase):

    def setUp(self):
        module_path = "cloudbaseinit.instrumentation.azure"

        self._module_patcher = mock.patch.dict(
            'sys.modules',
            {'six.moves': mock.MagicMock()})

        self._module_patcher.start()
        self._module = importlib.import_module(module_path)
        self._kvp = self._module.kvp = mock.MagicMock()
        self._constant = self._module.constant = mock.MagicMock()
        self._module.WindowsError = testutils.FakeWindowsError

        self._azure = self._module.AzureInstrumentation()
        self.snatcher = testutils.LogSnatcher(module_path)

    def tearDown(self):
        self._module_patcher.stop()

    def _test_initialize(self, configuration_pass):
        with testutils.ConfPatcher('configuration_pass', configuration_pass):
            self._azure.initialize()

    def test_initialize_no_delete_old_entries(self):
        self._test_initialize(not self._constant.CONFIGURATION_PASS_SPECIALIZE)

    def test_initialize(self):
        self._constant.CONFIGURATION_PASS_SPECIALIZE = \
            mock.sentinel.CONFIGURATION_PASS_SPECIALIZE
        self._test_initialize(self._constant.CONFIGURATION_PASS_SPECIALIZE)

    def test_delete_old_entries(self):
        expected_logging = ["Deleting existing KVP instrumentation values"]
        key_value_pairs = {
            "name": None,
            "specialize": None,
            "oobeSystem": None,
            "reportReady": None,
            "errorHandler": None
        }
        self._kvp.get_key_value_pairs.return_value = key_value_pairs
        with self.snatcher:
            self._azure._delete_old_entries()

        self.assertEqual(expected_logging, self.snatcher.output)
        self.assertEqual(
            sorted(self._kvp.delete_key_value_pair.call_args_list),
            sorted([mock.call("specialize"), mock.call("oobeSystem"),
                    mock.call("reportReady"), mock.call("errorHandler")]))

    def _test_instrument_call(self, exception, key, kvp_exception):
        expected_logging = []
        name = str(mock.sentinel.name)
        mock_callable = mock.MagicMock(return_value=mock.sentinel.ret_val)
        self._module.datetime = mock.MagicMock()
        mock_utcnow = mock.MagicMock()
        self._module.datetime.datetime.utcnow.return_value = mock_utcnow
        if key:
            mock_utcnow.strftime.side_effect = [
                str(mock.sentinel.start_time), str(mock.sentinel.end_time)]

        if exception:
            mock_callable.side_effect = exception
            cbinit_exc = self._module.exception.WindowsCloudbaseInitException
            if isinstance(exception, cbinit_exc):
                error_code = exception.error_code
            elif isinstance(exception, testutils.FakeWindowsError):
                error_code = exception.winerror
            else:
                error_code = self._kvp.DEFAULT_ERROR_CODE
        if kvp_exception:
            self._kvp.set_key_value_pair.side_effect = kvp_exception

        raised_exception = kvp_exception or exception
        config_pass_value = str(mock.sentinel.configuration_pass)
        with self.snatcher:
            with testutils.ConfPatcher('configuration_pass',
                                       config_pass_value):
                if raised_exception is None:
                    self._azure._PLUGIN_NAME_MAP[
                        (config_pass_value, name)] = key
                    result = self._azure.instrument_call(name, mock_callable)
                    self.assertEqual(result, mock_callable.return_value)
                else:
                    with self.assertRaises(raised_exception.__class__):
                        self._azure._PLUGIN_NAME_MAP[
                            (config_pass_value, name)] = key
                        self._azure.instrument_call(name, mock_callable)
        if key is None:
            expected_logging = [
                "No instrumentation key defined for: ('{}', '{}')".format(
                    mock.sentinel.configuration_pass, name)
            ]
        else:
            value = ("Called=%(start_time)s;"
                     "Returned=%(end_time)s;"
                     "ErrorCode=%(error_code)s" %
                     {"start_time": str(mock.sentinel.start_time),
                      "end_time": str(mock.sentinel.end_time),
                      "error_code": error_code})
            self._kvp.set_key_value_pair.assert_called_once_with(key, value)
            mock_utcnow.strftime.assert_has_calls(
                2 * [mock.call(self._module.DATETIME_FORMAT_STR)])

        self.assertEqual(expected_logging, self.snatcher.output)
        self._module.datetime.datetime.utcnow.has_calls(2 * [mock.call()])
        mock_callable.assert_called_once_with()

    def test_instrument_call_no_key_no_error(self):
        self._test_instrument_call(None, None, None)

    def test_instrument_call_CloudbaseInitException(self):
        with mock.patch('cloudbaseinit.exception.ctypes.FormatError',
                        create=True):
            with mock.patch('cloudbaseinit.exception.ctypes.GetLastError',
                            create=True):
                ex = self._module.exception.WindowsCloudbaseInitException()
                self._test_instrument_call(ex, None, None)

    def test_instrument_call_WindowsError(self):
        exception = testutils.FakeWindowsError(winerror=mock.sentinel.winerror)
        self._test_instrument_call(exception, mock.sentinel.key, None)

    def test_instrument_call_Exception(self):
        exception = Exception()
        self._test_instrument_call(exception, None, None)
