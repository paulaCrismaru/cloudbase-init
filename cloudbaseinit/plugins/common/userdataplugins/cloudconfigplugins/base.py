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

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BaseCloudConfigPlugin(object):
    """Base plugin class for cloud-config plugins."""

    @abc.abstractmethod
    def _execute(self, part, service=None):
        """Abstract method for processing the given data."""

    @property
    def keys(cls):
        return cls._keys

    def _get_used_key(self, part):
        if type(part) is not dict:
            pass
        elif type(self.keys) is not list and part.get(self.keys):
            return self.keys
        else:
            for key in self.keys:
                if part.get(key):
                    return key
        return None

    def execute(self, part, service=None):
        reboot_required = False
        plugin_key = self._get_used_key(part)
        if plugin_key:
            reboot_required = self._execute(part, service)
        return reboot_required
