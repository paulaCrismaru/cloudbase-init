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

import unittest

from cloudbaseinit.instrumentation import base


class TestNoOpInstrumentation(unittest.TestCase):

    def setUp(self):
        self._instr = base.NoOpInstrumentation()

    def test_instrument_call(self):
        expected_result = "fake result"
        result = self._instr.instrument_call(
            None, lambda: expected_result)
        self.assertEqual(result, expected_result)
