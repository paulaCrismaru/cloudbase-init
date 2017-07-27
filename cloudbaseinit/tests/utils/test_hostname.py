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

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.tests import testutils
from cloudbaseinit.utils import hostname

CONF = cloudbaseinit_conf.CONF


class HostnameUtilsTest(unittest.TestCase):

    @testutils.ConfPatcher('netbios_host_name_compatibility', True)
    def _test_set_hostname(self, new_hostname='hostname',
                           expected_new_hostname='hostname',
                           hostname_already_set=False,
                           set_fqdn=False):
        mock_osutils = mock.MagicMock()
        mock_osutils.set_host_name.return_value = True

        if hostname_already_set:
            mock_osutils.get_host_name.return_value = expected_new_hostname
        else:
            mock_osutils.get_host_name.return_value = 'fake_old_hostname'
        if set_fqdn:
            mock_osutils.set_primary_dns.return_value = True
            mock_osutils.get_host_name.side_effect = [
                mock_osutils.get_host_name.return_value,
                new_hostname
            ]
        (new_hostname, reboot_required) = hostname.set_hostname(
            mock_osutils, new_hostname)

        if hostname_already_set:
            self.assertFalse(mock_osutils.set_host_name.called)
        else:
            mock_osutils.set_host_name.assert_called_once_with(
                expected_new_hostname)

        self.assertEqual((new_hostname, reboot_required),
                         (expected_new_hostname, not hostname_already_set))

    def test_execute_hostname_already_set(self):
        self._test_set_hostname(hostname_already_set=True)

    def test_execute_hostname_to_be_truncated(self):
        new_hostname = 'x' * (hostname.NETBIOS_HOST_NAME_MAX_LEN + 1)
        expected_new_hostname = new_hostname[:-1]
        with testutils.LogSnatcher('cloudbaseinit.utils.'
                                   'hostname') as snatcher:
            self._test_set_hostname(
                new_hostname=new_hostname,
                expected_new_hostname=expected_new_hostname)

        expected = [
            'Truncating host name for Netbios compatibility. '
            'Old name: {0}, new name: {1}'.format(
                new_hostname, expected_new_hostname),
            'Setting hostname: xxxxxxxxxxxxxxx',
            "FQDN already set to: ''"
        ]
        self.assertEqual(expected, snatcher.output)

    def test_execute_no_truncate_needed(self):
        new_hostname = 'x' * hostname.NETBIOS_HOST_NAME_MAX_LEN
        expected_new_hostname = 'x' * hostname.NETBIOS_HOST_NAME_MAX_LEN
        self._test_set_hostname(new_hostname=new_hostname,
                                expected_new_hostname=expected_new_hostname)

    def test_execute_truncate_to_zero(self):
        new_hostname = 'x' * (hostname.NETBIOS_HOST_NAME_MAX_LEN - 1) + '-'
        expected_new_hostname = 'x' * (
            hostname.NETBIOS_HOST_NAME_MAX_LEN - 1) + '0'
        self._test_set_hostname(new_hostname=new_hostname,
                                expected_new_hostname=expected_new_hostname)

    def test_execute_set_fqdn(self):
        expected_new_hostname = "hostname"
        fqdn = "fake.fqdn"
        new_hostname = '.'.join([expected_new_hostname, fqdn])
        with testutils.LogSnatcher('cloudbaseinit.utils.'
                                   'hostname') as snatcher:
            self._test_set_hostname(
                set_fqdn=True,
                new_hostname=new_hostname,
                expected_new_hostname=expected_new_hostname)

        expected = [
            'Setting hostname: %s' % expected_new_hostname,
            "FQDN already set to: '%s'" % fqdn
        ]
        self.assertEqual(expected, snatcher.output)
