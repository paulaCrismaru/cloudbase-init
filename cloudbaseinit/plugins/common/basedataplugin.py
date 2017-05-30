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

import abc
import email
import os

from oslo_log import log as oslo_logging

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit import exception
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins.common import base
from cloudbaseinit.plugins.common import execcmd
from cloudbaseinit.plugins.common.userdataplugins import factory
from cloudbaseinit.plugins.common import userdatautils
from cloudbaseinit.utils import encoding
from cloudbaseinit.utils import x509constants


CONF = cloudbaseinit_conf.CONF
LOG = oslo_logging.getLogger(__name__)


class BaseUserdataPlugin(base.BasePlugin):
    _PART_HANDLER_CONTENT_TYPE = "text/part-handler"
    _GZIP_MAGIC_NUMBER = b'\x1f\x8b'

    @abc.abstractmethod
    def execute(self, service, shared_data):
        pass

    @staticmethod
    def _write_data(data, data_path):
        dir_path = os.path.dirname(data_path)

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        elif not os.path.isdir(dir_path):
            raise exception.CloudbaseInitException(
                'Path "%s" exists but it is not a directory' % dir_path)

        osutils = osutils_factory.get_os_utils()
        osutils.set_path_admin_acls(dir_path)

        if os.path.exists(data_path):
            osutils.take_path_ownership(data_path)
            os.unlink(data_path)

        LOG.debug("Writing userdata to: %s", data_path)
        encoding.write_file(data_path, data, mode='wb')

    @staticmethod
    def _parse_mime(data):
        LOG.debug('Data content:\n%s', data)
        return email.message_from_string(data).walk()

    @staticmethod
    def _get_headers(data):
        """Returns the header of the given user data.

        :param user_data: Represents the content of the user data.
        :rtype: A string chunk containing the header or None.
        .. note :: In case the content type is not valid,
                   None will be returned.
        """
        if data:
            return data.split("\n\n")[0]
        else:
            raise exception.CloudbaseInitException("No header could be found."
                                                   "The user data content is "
                                                   "either invalid or empty.")

    def _process_data(self, data):
        plugin_status = base.PLUGIN_EXECUTION_DONE
        reboot = False
        headers = self._get_headers(data)
        if 'Content-Type: multipart' in headers:
            LOG.debug("Processing userdata")
            data_plugins = factory.load_plugins()
            handlers = {}

            for part in self._parse_mime(data):
                (plugin_status, reboot) = self._process_part(part,
                                                             data_plugins,
                                                             handlers)
                if reboot:
                    break

            if not reboot:
                for handler_func in list(set(handlers.values())):
                    self._end_part_process_event(handler_func)

            return plugin_status, reboot
        else:
            return self._process_non_multi_part(data)

    def _process_part(self, part, data_plugins, handlers):
        ret_val = None
        try:
            content_type = part.get_content_type()

            handler_func = handlers.get(content_type)
            if handler_func:
                LOG.debug("Calling user part handler for content type: %s" %
                          content_type)
                handler_func(None, content_type, part.get_filename(),
                             part.get_payload())
            else:
                data_plugin = data_plugins.get(content_type)
                if not data_plugin:
                    LOG.info("Userdata plugin not found for content type: %s" %
                             content_type)
                else:
                    LOG.debug("Executing userdata plugin: %s" %
                              data_plugin.__class__.__name__)

                    if content_type == self._PART_HANDLER_CONTENT_TYPE:
                        new_handlers = data_plugin.process(part)
                        self._add_part_handlers(data_plugins,
                                                handlers,
                                                new_handlers)
                    else:
                        ret_val = data_plugin.process(part)
        except Exception as ex:
            LOG.error('Exception during multipart part handling: '
                      '%(content_type)s, %(filename)s' %
                      {'content_type': part.get_content_type(),
                       'filename': part.get_filename()})
            LOG.exception(ex)

        return execcmd.get_plugin_return_value(ret_val)

    def _add_part_handlers(self, data_plugins, handlers,
                           new_handlers):
        handler_funcs = set()

        for (content_type,
             handler_func) in new_handlers.items():
            if not data_plugins.get(content_type):
                LOG.info("Adding part handler for content "
                         "type: %s" % content_type)
                handlers[content_type] = handler_func
                handler_funcs.add(handler_func)
            else:
                LOG.info("Skipping part handler for content type \"%s\" as it "
                         "is already managed by a plugin" % content_type)

        for handler_func in handler_funcs:
            self._begin_part_process_event(handler_func)

    def _begin_part_process_event(self, handler_func):
        LOG.debug("Calling part handler \"__begin__\" event")
        handler_func(None, "__begin__", None, None)

    def _end_part_process_event(self, handler_func):
        LOG.debug("Calling part handler \"__end__\" event")
        handler_func(None, "__end__", None, None)

    def _process_non_multi_part(self, data):
        ret_val = None
        if data.startswith('#cloud-config'):
            user_data_plugins = factory.load_plugins()
            cloud_config_plugin = user_data_plugins.get('text/cloud-config')
            ret_val = cloud_config_plugin.process_non_multipart(data)
        elif data.strip().startswith(x509constants.PEM_HEADER):
            LOG.debug('Found X509 certificate in userdata')
        else:
            ret_val = userdatautils.execute_user_data_script(
                data.encode())

        return execcmd.get_plugin_return_value(ret_val)
