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


class TestKVP(testutils.CloudbaseInitTestBase):

    def setUp(self):
        self.mock_moves = mock.MagicMock()
        module_path = "cloudbaseinit.utils.windows.kvp"
        _module_patcher = mock.patch.dict(
            'sys.modules',
            {'six.moves': self.mock_moves})

        _module_patcher.start()
        self.addCleanup(_module_patcher.stop)
        self._winreg_mock = self.mock_moves.winreg
        self._kvp = importlib.import_module(module_path)
        self._kvp.winreg = self._winreg_mock
        self._kvp.WindowsError = testutils.FakeWindowsError

        self.snatcher = testutils.LogSnatcher(module_path)

    def test_set_key_value_pair(self):
        name = str(mock.sentinel.name)
        value = str(mock.sentinel.value)
        expected_logging = [
            "Setting KVP: {name} = {value}".format(name=name, value=value)
        ]
        with self.snatcher:
            self._kvp.set_key_value_pair(name, value)

        self.assertEqual(expected_logging, self.snatcher.output)
        self._winreg_mock.OpenKey.assert_called_once_with(
            self._winreg_mock.HKEY_LOCAL_MACHINE, self._kvp.KVP_REGISTRY_KEY,
            0, self._winreg_mock.KEY_ALL_ACCESS)
        self._winreg_mock.SetValueEx.assert_called_once_with(
            self._winreg_mock.OpenKey.return_value.__enter__(), name,
            0, self._winreg_mock.REG_SZ, str(value))

    def _handle_exception(self, exception, function, name):
        if exception.winerror == 2:
            expected_error = self._kvp.exception.ItemNotFoundException
        else:
            expected_error = testutils.FakeWindowsError
        with self.assertRaises(expected_error):
            with self.snatcher:
                function(name)

    def _test_get_key_value_pair(self, exception):
        name = str(mock.sentinel.name)
        expected_logging = ["Getting KVP value for: %s" % name]
        if exception is None:
            self._winreg_mock.QueryValueEx.return_value = [mock.sentinel.value]
            with self.snatcher:
                result = self._kvp.get_key_value_pair(name)
            self.assertEqual(result, mock.sentinel.value)
        else:
            self._winreg_mock.QueryValueEx.side_effect = [exception]
            self._handle_exception(exception, self._kvp.get_key_value_pair,
                                   name)
        self.assertEqual(expected_logging, self.snatcher.output)
        self._winreg_mock.OpenKey.assert_called_once_with(
            self._winreg_mock.HKEY_LOCAL_MACHINE, self._kvp.KVP_REGISTRY_KEY)
        self._winreg_mock.QueryValueEx.assert_called_once_with(
            self._winreg_mock.OpenKey.return_value.__enter__(), name)

    def test_get_key_value_pair(self):
        self._test_get_key_value_pair(None)

    def test_get_key_value_pair_key_not_found(self):
        exception = testutils.FakeWindowsError(winerror=2)
        self._test_get_key_value_pair(exception)

    def test_get_key_value_pair_exception(self):
        exception = testutils.FakeWindowsError(winerror=mock.sentinel.winerror)
        self._test_get_key_value_pair(exception)

    def _test_delete_key_value_pair(self, exception):
        name = str(mock.sentinel.name)
        expected_logging = ["Deleting KVP: %s" % name]
        if exception is None:
            with self.snatcher:
                self._kvp.delete_key_value_pair(name)
        else:
            self._winreg_mock.DeleteValue.side_effect = [exception]
            self._handle_exception(exception, self._kvp.delete_key_value_pair,
                                   name)
        self.assertEqual(expected_logging, self.snatcher.output)
        self._winreg_mock.OpenKey.assert_called_once_with(
            self._winreg_mock.HKEY_LOCAL_MACHINE, self._kvp.KVP_REGISTRY_KEY,
            0, self._winreg_mock.KEY_ALL_ACCESS)
        self._winreg_mock.DeleteValue.assert_called_once_with(
            self._winreg_mock.OpenKey.return_value.__enter__(), name)

    def test_delete_key_value_pair(self):
        self._test_delete_key_value_pair(None)

    def test_delete_key_value_pair_key_not_found(self):
        exception = testutils.FakeWindowsError(winerror=2)
        self._test_delete_key_value_pair(exception)

    def test_delete_key_value_pair_exception(self):
        exception = testutils.FakeWindowsError(winerror=mock.sentinel.winerror)
        self._test_delete_key_value_pair(exception)

    def _test_get_value_pairs(self, error_code=259):
        expected_logging = ["Getting KVPs"]
        side_effect = [
            (str(mock.sentinel.name), mock.sentinel.value, None),
            (str(mock.sentinel.name2), mock.sentinel.value2, None),
            (str(mock.sentinel.name), mock.sentinel.value0, None),
            (str(mock.sentinel.name3), mock.sentinel.value3, None),
            testutils.FakeWindowsError(winerror=error_code)
        ]
        self._winreg_mock.EnumValue.side_effect = side_effect
        expected_kvps = {
            str(mock.sentinel.name): mock.sentinel.value0,
            str(mock.sentinel.name2): mock.sentinel.value2,
            str(mock.sentinel.name3): mock.sentinel.value3,
        }
        with self.snatcher:
            if error_code != 259:
                with self.assertRaises(testutils.FakeWindowsError):
                    self._kvp.get_key_value_pairs()
            else:
                result = self._kvp.get_key_value_pairs()
                self.assertEqual(result, expected_kvps)

        self.assertEqual(expected_logging, self.snatcher.output)
        self._winreg_mock.OpenKey.assert_called_once_with(
            self._winreg_mock.HKEY_LOCAL_MACHINE, self._kvp.KVP_REGISTRY_KEY)
        self._winreg_mock.EnumValue.assert_has_calls(
            [mock.call(self._winreg_mock.OpenKey.return_value.__enter__(), i)
             for i in range(len(side_effect))])

    def test_get_value_pairs(self):
        self._test_get_value_pairs()

    def test_get_value_pairs_exception(self):
        self._test_get_value_pairs(mock.sentinel.error_code)
