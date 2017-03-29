from oslo_versionedobjects import base as ovoo_base
from oslo_versionedobjects import fields


def get_attrname(name):
    return '_obj_' + name


class IPAddressField(fields.IPAddressField):

    def obj_load_attr(self, attrname):
        try:
            getattr(self, attrname)
        except AttributeError:
            if self.fields.get(attrname).default == fields.UnspecifiedDefault:
                setattr(self, attrname, None)
            else:
                setattr(self, attrname, self.fields.get(attrname).default)


class StringField(fields.StringField):

    def obj_load_attr(self, attrname):
        try:
            getattr(self, attrname)
        except AttributeError:
            if self.fields.get(attrname).default == fields.UnspecifiedDefault:
                setattr(self, attrname, None)
            else:
                setattr(self, attrname, self.fields.get(attrname).default)


class MACAddressField(fields.MACAddressField):

    def obj_load_attr(self, attrname):
        try:
            getattr(self, attrname)
        except AttributeError:
            if self.fields.get(attrname).default == fields.UnspecifiedDefault:
                setattr(self, attrname, None)
            else:
                setattr(self, attrname, self.fields.get(attrname).default)


class ListOfIPAddressField(fields.AutoTypedField):
    AUTO_TYPE = fields.List(fields.IPAddress())


@ovoo_base.VersionedObjectRegistry.register
class NIC(ovoo_base.VersionedObject):

    OBJ_SERIAL_NAMESPACE = 'network_object'
    OBJ_PROJECT_NAMESPACE = 'cloudbaseinit'

    fields = {
        "name": StringField(),
        "mac": MACAddressField(nullable=True),
        "address": IPAddressField(),
        "address6": IPAddressField(),
        "netmask": IPAddressField(),
        "netmask6": IPAddressField(),
        "broadcast": IPAddressField(),
        "gateway": IPAddressField(),
        "gateway6": IPAddressField(),
        "dnsnameservers": ListOfIPAddressField()

    }

    def obj_load_attr(self, attrname):
        default_value = self.fields.get(attrname).default
        if default_value == fields.UnspecifiedDefault:
            setattr(self, get_attrname(attrname), None)
        else:
            setattr(self, get_attrname(attrname), default_value)
