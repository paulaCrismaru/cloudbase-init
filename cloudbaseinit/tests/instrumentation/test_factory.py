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
import unittest

from cloudbaseinit.instrumentation import factory
from cloudbaseinit.tests import testutils


class FakeClass(object):
    pass


class TestFactory(unittest.TestCase):

    def _test_load_instrumentation(self, instrumentation_class_path):
        if instrumentation_class_path is not None:
            module_path = '.'.join(instrumentation_class_path.split('.')[:-1])
            module = importlib.import_module(module_path)
            class_name = instrumentation_class_path.split('.')[-1]
            instrumentation_class = getattr(module, class_name)
        else:
            instrumentation_class = factory.base.NoOpInstrumentation
        with testutils.ConfPatcher('instrumentation_class',
                                   instrumentation_class_path):
            result = factory.load_instrumentation()
        self.assertTrue(isinstance(result, instrumentation_class))

    def test_load_instrumentation(self):
        module_path = ('cloudbaseinit.tests.instrumentation.'
                       'test_factory.FakeClass')
        self._test_load_instrumentation(module_path)

    def test_load_instrumentation_no_class(self):
        self._test_load_instrumentation(None)
