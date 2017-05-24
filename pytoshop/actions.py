# -*- coding: utf-8 -*-


"""
Handles the "Action" data types.
"""


import six


from . import enums
from . import util


def _write_zero_if_four(fd, value):
    if value == 4:
        util.write_value(fd, 'I', 0)
    else:
        util.write_value(fd, 'I', value)


class _OSTypeMeta(type):
    """
    A metaclass that builds a mapping of subclasses.
    """
    mapping = {}

    def __new__(cls, name, parents, dct):
        new_cls = type.__new__(cls, name, parents, dct)

        if '_code' in dct and isinstance(dct['_code'], bytes):
            code = dct['_code']
            if code in cls.mapping:
                raise ValueError("Duplicate code '{}'".format(code))
            cls.mapping[code] = new_cls

        return new_cls


def get_ostype(code):
    if code not in _OSTypeMeta.mapping:
        raise ValueError("Unknown ostype '{}'".format(code))
    return _OSTypeMeta.mapping[code]


@six.add_metaclass(_OSTypeMeta)
class OSType(object):
    @property
    def code(self):
        return self._code


class _RefOSTypeMeta(type):
    """
    A metaclass that builds a mapping of subclasses.
    """
    mapping = {}

    def __new__(cls, name, parents, dct):
        new_cls = type.__new__(cls, name, parents, dct)

        if '_code' in dct and isinstance(dct['_code'], bytes):
            code = dct['_code']
            if code in cls.mapping:
                raise ValueError("Duplicate code '{}'".format(code))
            cls.mapping[code] = new_cls

        return new_cls


def get_ref_ostype(code):
    if code not in _RefOSTypeMeta.mapping:
        raise ValueError("Unknown ostype '{}'".format(code))
    return _RefOSTypeMeta.mapping[code]


@six.add_metaclass(_RefOSTypeMeta)
class RefOSType(object):
    @property
    def code(self):
        return self._code


class Descriptor(OSType):
    _code = enums.OSType.descriptor.value

    def __init__(self, name='', class_id=b'null', items=None):
        self.name = name
        self.class_id = class_id
        if items is None:
            items = []
        self.items = items

    @property
    def name(self):
        "Name from class id."
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, six.text_type):
            raise TypeError("name must be a string")
        self._name = value

    @property
    def class_id(self):
        "Class ID."
        return self._class_id

    @class_id.setter
    def class_id(self, value):
        if not isinstance(value, bytes):
            raise TypeError("class_id must be a bytes string")
        self._class_id = value

    @property
    def items(self):
        "Items in descriptor. List of OSType."
        return self._items

    @items.setter
    def items(self, value):
        if not isinstance(value, list):
            raise ValueError("items must be a list")
        for item in value:
            if (not isinstance(item, tuple) or len(item) != 2 or
                    not isinstance(item[0], bytes) or
                    not isinstance(item[1], OSType)):
                raise ValueError(
                    "items must be a list of (bytes, OSType) pairs"
                )

        self._items = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        name = util.read_unicode_string(fd)
        class_id_length = util.read_value(fd, "I")
        class_id = fd.read(class_id_length or 4)

        util.log("class_id: {}", class_id)

        items = []
        item_count = util.read_value(fd, "I")

        util.log("item_count: {}", item_count)
        for i in range(item_count):
            item_length = util.read_value(fd, "I")
            key = fd.read(item_length or 4)

            util.log('key: {}', key)

            ostype = fd.read(4)
            ostype_cls = get_ostype(ostype)
            value = ostype_cls.read(fd)
            if value is not None:
                items.append((key, value))

        util.log(
            "name: {}, class_id: {}, len(items): {}",
            name, class_id, len(items)
        )

        return cls(
            name=name,
            class_id=class_id,
            items=items
        )

    @util.trace_write
    def write(self, fd):
        util.write_unicode_string(fd, self.name)
        _write_zero_if_four(fd, len(self.class_id))
        fd.write(self.class_id)
        util.write_value(fd, 'I', len(self.items))
        for key, value in self.items:
            _write_zero_if_four(fd, len(key))
            fd.write(key)
            fd.write(value.code)
            value.write(fd)


class GlobalObject(Descriptor):
    _code = enums.OSType.global_object


class Reference(OSType):
    _code = enums.OSType.reference.value

    def __init__(self, items=None):
        if items is None:
            items = []
        self.items = items

    @property
    def items(self):
        "Items in descriptor. List of OSType."
        return self._items

    @items.setter
    def items(self, value):
        util.assert_is_list_of(value, OSType)
        self._items = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        item_count = util.read_value(fd, 'I')

        util.log("item_count: {}", item_count)

        items = []
        for i in range(item_count):
            ostype = fd.read(4)

            ostype_cls = get_ref_ostype(ostype)
            value = ostype_cls.read(fd)
            if value is not None:
                items.append(value)

        return cls(items=items)

    @util.trace_write
    def write(self, fd):
        util.write_value(fd, 'I', len(self.items))
        for item in self.items:
            fd.write(item.code)
            item.write(fd)


class Property(RefOSType):
    _code = enums.RefOSType.property.value

    def __init__(self, name='', class_id=b'', key_id=b''):
        self.name = name
        self.class_id = class_id
        self.key_id = key_id

    @property
    def name(self):
        "Name from class id."
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, six.text_type):
            raise TypeError("name must be a string")
        self._name = value

    @property
    def class_id(self):
        "Class ID."
        return self._class_id

    @class_id.setter
    def class_id(self, value):
        if not isinstance(value, bytes):
            raise TypeError("class_id must be a bytes string")
        self._class_id = value

    @property
    def key_id(self):
        "Key ID."
        return self._key_id

    @key_id.setter
    def key_id(self, value):
        if not isinstance(value, bytes):
            raise TypeError("key_id must be a bytes string")
        self._key_id = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        name = util.read_unicode_string(fd)
        class_id_length = util.read_value(fd, 'I')
        class_id = fd.read(class_id_length or 4)
        key_id_length = util.read_value(fd, 'I')
        key_id = fd.read(key_id_length or 4)

        util.log(
            "name: {}, class_id: {}, key_id: {}",
            name, class_id, key_id
        )

        return cls(
            name=name,
            class_id=class_id,
            key_id=key_id
        )

    @util.trace_write
    def write(self, fd):
        util.write_unicode_string(fd, self.name)
        _write_zero_if_four(fd, len(self.class_id))
        fd.write(self._class_id)
        _write_zero_if_four(fd, len(self.key_id))
        fd.write(self._key_id)


class UnitFloat(OSType):
    _code = enums.OSType.unit_float.value

    def __init__(self, unit, value):
        self.unit = unit
        self.value = value

    @property
    def unit(self):
        "Units the value is in."
        return self._unit

    @unit.setter
    def unit(self, value):
        if value not in list(x.value for x in enums.OSTypeUnit):
            raise ValueError("Invalid unit '{}'".format(value))
        self._unit = value

    @property
    def value(self):
        "Actual value."
        return self._value

    @value.setter
    def value(self, value):
        if not isinstance(value, float):
            raise TypeError("Value must be a float instance")
        self._value = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        unit = fd.read(4)
        value = util.read_value(fd, 'd')

        util.log("unit: {}, value: {}", unit, value)

        return cls(unit=unit, value=value)

    @util.trace_write
    def write(self, fd):
        fd.write(self.unit)
        util.write_value(fd, 'd', self.value)


class UnitFloats(OSType):
    _code = enums.OSType.unit_floats.value

    def __init__(self, unit, values):
        self.unit = unit
        self.values = values

    @property
    def unit(self):
        "Units the value is in."
        return self._unit

    @unit.setter
    def unit(self, value):
        if value not in list(x.value for x in enums.OSTypeUnit):
            raise ValueError("Invalid unit '{}'".format(value))
        self._unit = value

    @property
    def values(self):
        "List of actual values."
        return self._values

    @values.setter
    def values(self, value):
        util.assert_is_list_of(value, float)
        self._values = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        unit = fd.read(4)
        floats_count = util.read_value(fd, 'I')

        util.log("unit: {}, count: {}", unit, floats_count)

        floats = []
        for i in range(floats_count):
            value = util.read_value(fd, 'd')
            floats.append(value)
        return cls(unit=unit, values=floats)

    @util.trace_write
    def write(self, fd):
        fd.write(self.unit)
        util.write_value(fd, 'I', len(self.values))
        for value in self.values:
            util.write_value(fd, 'd', value)


class Double(OSType):
    _code = enums.OSType.double.value

    def __init__(self, value):
        self.value = value

    @property
    def value(self):
        "Actual value."
        return self._value

    @value.setter
    def value(self, value):
        if not isinstance(value, float):
            raise TypeError("Value must be a float instance")
        self._value = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        value = util.read_value(fd, 'd')

        util.log("value: {}", value)

        return cls(value=value)

    @util.trace_write
    def write(self, fd):
        util.write_value(fd, 'd', self.value)


class _ClassBase(object):
    def __init__(self, name='', class_id=b''):
        self.name = name
        self.class_id = class_id

    @property
    def name(self):
        "Name from class id."
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, six.text_type):
            raise TypeError("name must be a string")
        self._name = value

    @property
    def class_id(self):
        "Class ID."
        return self._class_id

    @class_id.setter
    def class_id(self, value):
        if not isinstance(value, bytes):
            raise TypeError("class_id must be a bytes string")
        self._class_id = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        name = util.read_unicode_string(fd)
        class_id_length = util.read_value(fd, 'I')
        class_id = fd.read(class_id_length or 4)

        util.log("name: {}, class_id: {}", name, class_id)

        return cls(name=name, class_id=class_id)

    @util.trace_write
    def write(self, fd):
        util.write_unicode_string(fd, self.name)
        _write_zero_if_four(fd, len(self.class_id))
        fd.write(self.class_id)


class Class1(_ClassBase, OSType):
    _code = enums.OSType.class1.value


class Class2(_ClassBase, OSType):
    _code = enums.OSType.class2.value


class ClassRef(_ClassBase, RefOSType):
    _code = enums.RefOSType.cls.value


class _StringBase(object):
    def __init__(self, value=''):
        self.value = value

    @property
    def value(self):
        "Actual value."
        return self._value

    @value.setter
    def value(self, value):
        if not isinstance(value, six.text_type):
            raise TypeError("Value must be a unicode instance")
        self._value = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        value = util.read_unicode_string(fd)

        util.log("value: {}", value)

        return cls(value=value)

    @util.trace_write
    def write(self, fd):
        util.write_unicode_string(fd, self.value)


class String(_StringBase, OSType):
    _code = enums.OSType.string.value


class EnumeratedRef(RefOSType):
    _code = enums.RefOSType.enumerated_reference.value

    def __init__(self, name='', class_id=b'', type_id=b'', enum=b''):
        self.name = name
        self.class_id = class_id
        self.type_id = type_id
        self.enum = enum

    @property
    def name(self):
        "Name from class id."
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, six.text_type):
            raise TypeError("name must be a string")
        self._name = value

    @property
    def class_id(self):
        "Class ID."
        return self._class_id

    @class_id.setter
    def class_id(self, value):
        if not isinstance(value, bytes):
            raise TypeError("class_id must be a bytes string")
        self._class_id = value

    @property
    def type_id(self):
        "Type ID."
        return self._type_id

    @type_id.setter
    def type_id(self, value):
        if not isinstance(value, bytes):
            raise TypeError("type_id must be a bytes string")
        self._type_id = value

    @property
    def enum(self):
        "Type ID."
        return self._enum

    @enum.setter
    def enum(self, value):
        if not isinstance(value, bytes):
            raise TypeError("enum must be a bytes string")
        self._enum = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        name = util.read_unicode_string(fd)
        class_id_length = util.read_value(fd, 'I')
        class_id = fd.read(class_id_length or 4)
        type_id_length = util.read_value(fd, 'I')
        type_id = fd.read(type_id_length or 4)
        enum_length = util.read_value(fd, 'I')
        enum = fd.read(enum_length or 4)

        util.log(
            "name: {}, class_id: {}, type_id: {}, enum: {}",
            name, class_id, type_id, enum
        )

        return cls(name=name, class_id=class_id, type_id=type_id, enum=enum)

    @util.trace_write
    def write(self, fd):
        util.write_unicode_string(fd, self.name)
        _write_zero_if_four(fd, len(self.class_id))
        fd.write(self.class_id)
        _write_zero_if_four(fd, len(self.type_id))
        fd.write(self.type_id)
        _write_zero_if_four(fd, len(self.enum))
        fd.write(self.enum)


class Offset(RefOSType):
    _code = enums.RefOSType.offset.value

    def __init__(self, name='', class_id=b'', offset=0):
        self.name = name,
        self.class_id = class_id
        self.offset = offset

    @property
    def name(self):
        "Name from class id."
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, six.text_type):
            raise TypeError("name must be a string")
        self._name = value

    @property
    def class_id(self):
        "Class ID."
        return self._class_id

    @class_id.setter
    def class_id(self, value):
        if not isinstance(value, bytes):
            raise TypeError("class_id must be a bytes string")
        self._class_id = value

    @property
    def offset(self):
        "Value of the offset."
        return self._offset

    @offset.setter
    def offset(self, value):
        if not isinstance(value, int) or value < 0:
            raise TypeError("offset must be a non-negative integer.")
        self._offset = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        name = util.read_unicode_string(fd)
        class_id_length = util.read_value(fd, 'I')
        class_id = fd.read(class_id_length or 4)
        offset = util.read_value(fd, 'I')

        util.log(
            "name: {}, class_id: {}, offset: {}",
            name, class_id, offset
        )

        return cls(name=name, class_id=class_id, offset=offset)

    @util.trace_write
    def write(self, fd):
        util.write_unicode_string(fd, self.name)
        _write_zero_if_four(fd, len(self.class_id))
        fd.write(self.class_id)
        util.write_value(fd, 'I', self.offset)


class Boolean(OSType):
    _code = enums.OSType.boolean.value

    def __init__(self, value=False):
        self.value = value

    @property
    def value(self):
        "Boolean value"
        return self._value

    @value.setter
    def value(self, value):
        self._value = bool(value)

    @classmethod
    @util.trace_read
    def read(cls, fd):
        value = fd.read_value(fd, '?')

        util.log("value: {}", value)

        return cls(value=value)

    @util.trace_write
    def write(self, fd):
        util.write_value(fd, '?', self.value)


class Alias(OSType):
    _code = enums.OSType.alias.value

    def __init__(self, value=b''):
        self.value = value

    @property
    def value(self):
        """
        FSSpec for Macintosh or a handle to a string to the full path on
        Windows
        """
        return self._value

    @value.setter
    def value(self, value):
        if not isinstance(value, bytes):
            raise TypeError("Invalid value '{}'".format(value))

    @classmethod
    @util.trace_read
    def read(cls, fd):
        length = util.read_value(fd, 'I')
        value = fd.read(length)

        util.log("value: {}", value)

        return cls(value=value)

    @util.trace_write
    def write(self, fd):
        util.write_value(fd, 'I', len(self.value))
        fd.write(self.value)


class List(OSType):
    _code = enums.OSType.list.value

    def __init__(self, items=None):
        if items is None:
            items = []
        self.items = items

    @property
    def items(self):
        "Items in the list"
        return self._items

    @items.setter
    def items(self, value):
        util.assert_is_list_of(value, OSType)
        self._items = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        items_count = util.read_value(fd, 'I')
        items = []

        util.log("items_count: {}", items_count)

        for i in range(items_count):
            ostype = fd.read(4)
            ostype_cls = get_ostype(ostype)
            value = ostype_cls.read(fd)
            if value is not None:
                items.append(value)

        return cls(items=items)

    @util.trace_write
    def write(self, fd):
        util.write_value(fd, 'I', len(self.items))
        for item in self.items:
            fd.write(item.code)
            item.write(fd)


class _IntegerBase(object):
    def __init__(self, value=0):
        self.value = value

    @property
    def value(self):
        "Actual value."
        return self._value

    @value.setter
    def value(self, value):
        if not isinstance(value, int):
            raise TypeError("Value must be an integer")
        self._value = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        value = util.read_value(fd, 'i')

        util.log('value: {}', value)

        return cls(value=value)

    @util.trace_write
    def write(self, fd):
        util.write_value(fd, 'i', self.value)


class Integer(_IntegerBase, OSType):
    _code = enums.OSType.integer.value


class LargeInteger(_IntegerBase, OSType):
    _code = enums.OSType.large_integer.value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        value = util.read_value(fd, 'q')

        util.log('value: {}', value)

        return cls(value=value)

    @util.trace_write
    def write(self, fd):
        util.write_value(fd, 'q', self.value)


class Enumerated(OSType):
    _code = enums.OSType.enumerated.value

    def __init__(self, enum_type=b'', value=b''):
        self.enum_type = enum_type
        self.value = value

    @property
    def enum_type(self):
        "Type of enumeration"
        return self._enum_type

    @enum_type.setter
    def enum_type(self, value):
        if not isinstance(value, bytes):
            raise TypeError("enum_type must be a bytes string")
        self._enum_type = value

    @property
    def value(self):
        "The enumeration value"
        return self._value

    @value.setter
    def value(self, value):
        if not isinstance(value, bytes):
            raise TypeError("value must be a bytes string")
        self._value = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        type_length = util.read_value(fd, 'I')
        enum_type = fd.read(type_length or 4)
        value_length = util.read_value(fd, 'I')
        value = fd.read(value_length or 4)

        util.log('enum_type: {}, value: {}', enum_type, value)

        return cls(enum_type=enum_type, value=value)

    @util.trace_write
    def write(self, fd):
        _write_zero_if_four(fd, len(self.enum_type))
        fd.write(self.enum_type)
        _write_zero_if_four(fd, len(self.value))
        fd.write(self.value)


class Identifier(_IntegerBase, RefOSType):
    _code = enums.RefOSType.identifier.value


class Index(_IntegerBase, RefOSType):
    _code = enums.RefOSType.index.value


class Name(_StringBase, RefOSType):
    _code = enums.RefOSType.name.value


class RawData(OSType):
    def __init__(self, value=''):
        self.value = value

    @property
    def value(self):
        "Actual value."
        return self._value

    @value.setter
    def value(self, value):
        if not isinstance(value, bytes):
            raise TypeError("Value must be a bytes instance")
        self._value = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        length = util.read_value(fd, 'I')
        value = fd.read(length)

        util.log("len(value): {}", len(value))

        return cls(value=value)

    @util.trace_write
    def write(self, fd):
        util.write_value(fd, 'I', len(self.value))
        fd.write(self.value)


class ObjectArray(OSType):
    _code = enums.OSType.object_array.value

    def __init__(self, class_obj, items):
        self.class_obj = class_obj
        self.items = items

    @property
    def class_obj(self):
        "The class object"
        return self._class_obj

    @class_obj.setter
    def class_obj(self, value):
        if not isinstance(value, _ClassBase):
            raise TypeError("class_obj must be a Class instance")
        self._class_obj = value

    @property
    def items(self):
        "Object array items"
        return self._items

    @items.setter
    def items(self, value):
        util.assert_is_list_of(value, ObjectArrayItem)
        self._items = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        items_per_object_count = util.read_value(fd, 'I')
        class_obj = Class1.read(fd)
        items_count = util.read_value(fd, 'I')
        items = []

        util.log(
            'items_per_object_count: {}, items_count: {}',
            items_per_object_count, items_count
        )

        for i in range(items_count):
            object_array_item = ObjectArrayItem.read(fd)
            if object_array_item is not None:
                items.append(object_array_item)

        return cls(class_obj=class_obj, items=items)

    @util.trace_write
    def write(self, fd):
        util.write_value(fd, 'I', 0)
        self.class_obj.write(fd)
        util.write_value(fd, 'I', len(self.items))
        for item in self.items:
            item.write(fd)


class ObjectArrayItem(object):
    def __init__(self, key_id=b'', value=None):
        self.key_id = key_id
        self.value = value

    @property
    def key_id(self):
        return self._key_id

    @key_id.setter
    def key_id(self, value):
        if not isinstance(value, bytes):
            raise TypeError("key_id must be a bytes string")
        self._key_id = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if not isinstance(value, OSType):
            raise TypeError("value must be an OSType instance")
        self._value = value

    @classmethod
    @util.trace_read
    def read(cls, fd):
        key_id_length = util.read_value(fd, 'I')
        key_id = fd.read(key_id_length or 4)
        ostype = fd.read(4)
        ostype_cls = get_ostype(ostype)
        value = ostype_cls.read(fd)
        return cls(key_id, value)

    @util.trace_write
    def write(self, fd):
        _write_zero_if_four(fd, len(self.key_id))
        fd.write(self.key_id)
        fd.write(self.value.code)
        self.value.write(fd)
