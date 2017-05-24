# -*- coding: utf-8 -*-


"""
`TaggedBlock` objects.
"""


from __future__ import unicode_literals, absolute_import


import six


from . import docs
from . import enums
from . import path
from . import util


class _TaggedBlockMeta(type):
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


@six.add_metaclass(_TaggedBlockMeta)
class TaggedBlock(object):
    _large_layer_info_codes = set([
        b'LMsk', b'Lr16', b'Lr32', b'Layr', b'Mt16', b'Mt32',
        b'Mtrn', b'Alph', b'FMsk', b'Ink2', b'FEid', b'FXid',
        b'PxSD', b'lnkD', b'lnk2', b'lnk3', b'lnkE'
    ])

    @property
    def code(self):
        return self._code

    def length(self, header):
        return self.data_length(header)
    length.__doc__ = docs.length

    def total_length(self, header, padding=1):
        length = 8
        if self.is_long_length(self.code, header):
            length += 8
        else:
            length += 4
        length += util.pad(self.length(header), padding)
        return length
    total_length.__doc__ = docs.total_length

    @staticmethod
    def is_long_length(code, header):
        return (
            (header.version == 2 and
             code in TaggedBlock._large_layer_info_codes)
        )

    @classmethod
    @util.trace_read
    def read(cls, fd, header, padding=1):
        signature = fd.read(4)
        if signature not in (b'8BIM', b'8B64'):
            raise ValueError('Invalid signature in tagged block')

        code = fd.read(4)

        if cls.is_long_length(code, header):
            length = util.read_value(fd, 'Q')
        else:
            length = util.read_value(fd, 'I')
        padded_length = util.pad(length, padding)

        util.log(
            "code: {}, length: {}, padded_length: {}",
            code, length, padded_length
        )

        new_cls = _TaggedBlockMeta.mapping.get(code, GenericTaggedBlock)
        start = fd.tell()
        result = new_cls.read_data(fd, code, length, header)
        end = fd.tell()
        if end - start != length:
            raise ValueError("{} read the wrong amount".format(new_cls))
        fd.seek(padded_length - length, 1)

        return result
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header, padding=1):
        if header.version == 2 and self.code in self._large_layer_info_codes:
            fd.write(b'8B64')
        else:
            fd.write(b'8BIM')
        fd.write(self.code)

        length = self.data_length(header)
        padded_length = util.pad(length, padding)
        if header.version == 2 and self.code in self._large_layer_info_codes:
            util.write_value(fd, 'Q', length)
        else:
            util.write_value(fd, 'I', length)

        start = fd.tell()
        self.write_data(fd, header)
        end = fd.tell()
        if end - start != length:
            raise ValueError(
                "{} wrote the wrong amount.  Expected {}, got {}".format(
                    self.__class__, length, end - start)
            )
        fd.write(b'\0' * (padded_length - length))
    write.__doc__ = docs.write


class GenericTaggedBlock(TaggedBlock):
    """
    A generic `TaggedBlock` subclass for tag codes ``pytoshop``
    doesn't know about.
    """

    def __init__(self, code=b'', data=b''):
        self._code = code
        self._data = data

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, val):
        if not isinstance(val, bytes) or len(val) != 4:
            raise ValueError("Code be 4-length bytes")
        self._code = val

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, val):
        if not isinstance(val, bytes):
            raise ValueError("Data must be bytes")

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        data = fd.read(length)
        util.log('data: {}', data)
        return cls(code=code, data=data)

    def data_length(self, header):
        return len(self.data)

    @util.trace_write
    def write_data(self, fd, header):
        fd.write(self.data)


class UnicodeLayerName(TaggedBlock):
    def __init__(self, name=''):
        self.name = name

    _code = b'luni'

    @property
    def name(self):
        "The name of the layer."
        return self._name

    @name.setter
    def name(self, value):
        if isinstance(value, bytes):
            value = value.decode('ascii')

        if (not isinstance(value, six.text_type) or
                len(value) > 255):
            raise ValueError("name must be unicode string of length < 255")
        self._name = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        data = fd.read(length)
        name = util.decode_unicode_string(data)
        return cls(name=name)

    def data_length(self, header):
        return len(util.encode_unicode_string(self.name))

    @util.trace_write
    def write_data(self, fd, header):
        fd.write(util.encode_unicode_string(self.name))


class LayerId(TaggedBlock):
    def __init__(self, id=0):
        self.id = id

    _code = b'lyid'

    @property
    def id(self):
        "Layer id"
        return self._id

    @id.setter
    def id(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("id must be a 32-bit integer")
        self._id = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        id = util.read_value(fd, 'I')
        util.log("id: {}", id)
        return cls(id=id)

    def data_length(self, header):
        return 4

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'I', self.id)


class LayerNameSource(TaggedBlock):
    def __init__(self, id=0):
        self.id = id

    _code = b'lnsr'

    @property
    def id(self):
        "The layer id of the source of the name of this layer"
        return self._id

    @id.setter
    def id(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("id must be a 32-bit integer")
        self._id = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        id = util.read_value(fd, 'I')
        util.log("id: {}", id)
        return cls(id=id)

    def data_length(self, header):
        return 4

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'I', self.id)


class _SectionDividerSetting(TaggedBlock):
    def __init__(self,
                 type=enums.SectionDividerSetting.open,
                 key=None,
                 subtype=None):
        self.type = type
        self.key = key
        self.subtype = subtype

    @property
    def type(self):
        "Section divider type. See `enums.SectionDividerSetting`."
        return self._type

    @type.setter
    def type(self, value):
        if value not in list(enums.SectionDividerSetting):
            raise ValueError("Invalid section divider setting")
        self._type = value

    @property
    def key(self):
        "Section divider key"
        return self._key

    @key.setter
    def key(self, value):
        if value is not None and value not in list(enums.BlendMode):
            raise ValueError("Invalid blend mode")
        self._key = value

    @property
    def subtype(self):
        """
        Section divider subtype. False=normal, True=Scene group,
        affects the animation timeline.
        """
        return self._subtype

    @subtype.setter
    def subtype(self, value):
        if value is None:
            self._subtype = value
        else:
            self._subtype = bool(value)

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        end = fd.tell() + length
        type = util.read_value(fd, 'I')
        key = None
        subtype = None
        if fd.tell() < end:
            sig = fd.read(4)
            if sig != b'8BIM':
                raise ValueError("Invalid signature")
            key = fd.read(4)
            if fd.tell() < end:
                subtype = bool(util.read_value(fd, 'I'))

        util.log(
            "type: {}, key: {}, subtype: {}",
            type, key, subtype
        )

        return cls(type=type, key=key, subtype=subtype)

    def data_length(self, header):
        length = 4
        if self.subtype is not None:
            length += 12
        elif self.key is not None:
            length += 8
        return length

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'I', self.type)
        if self.key is not None or self.subtype is not None:
            if self.key is None:
                key = b'norm'
            else:
                key = self.key
            fd.write(b'8BIM')
            fd.write(key)
            if self.subtype is not None:
                util.write_value(fd, 'I', self.subtype)


class SectionDividerSetting(_SectionDividerSetting):
    _code = b'lsct'


class NestedSectionDividerSetting(_SectionDividerSetting):
    _code = b'lsdk'


class VectorMask(TaggedBlock):
    def __init__(self,
                 version=3,
                 invert=False,
                 not_link=False,
                 disable=False,
                 path_resource=None):
        self.version = version
        self.invert = invert
        self.not_link = not_link
        self.disable = disable
        self.path_resource = path_resource

    _code = b'vmsk'

    @property
    def version(self):
        'Vector mask block version'
        return self._version

    @version.setter
    def version(self, value):
        if not isinstance(value, int):
            raise TypeError("version must be an int")
        self._version = value

    @property
    def invert(self):
        "Invert mask"
        return self._invert

    @invert.setter
    def invert(self, value):
        self._invert = bool(value)

    @property
    def not_link(self):
        "Don't link mask"
        return self._not_link

    @not_link.setter
    def not_link(self, value):
        self._not_link = bool(value)

    @property
    def disable(self):
        "Disable mask"
        return self._disable

    @disable.setter
    def disable(self, value):
        self._disable = bool(value)

    @property
    def path_resource(self):
        "`path.PathResource` instance`"
        return self._path_resource

    @path_resource.setter
    def path_resource(self, value):
        if not isinstance(value, path.PathResource):
            raise TypeError("path_resource must by a PathResource instance.")
        self._path_resource = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        version, flags = util.read_value(fd, 'II')
        invert, not_link, disable = util.unpack_bitflags(flags, 3)

        util.log(
            "version: {}, invert: {}, not_link: {}, disable: {}",
            version, invert, not_link, disable)

        path_resource = path.PathResource.read(fd, length - 8, header)

        return cls(
            version=version,
            invert=invert,
            not_link=not_link,
            disable=disable,
            path_resource=path_resource)

    def data_length(self, header):
        return 8 + self.path_resource.length(header)

    @util.trace_write
    def write_data(self, fd, header):
        flags = util.pack_bitflags(self.invert, self.not_link, self.disable)

        util.write_value(fd, 'II', self.version, flags)

        self.path_resource.write(fd, header)


class MetadataSetting(TaggedBlock):
    def __init__(self, datas=None):
        if datas is None:
            datas = {}
        self.datas = datas

    _code = b'shmd'

    @property
    def datas(self):
        return self._datas

    @datas.setter
    def datas(self, val):
        if not isinstance(val, dict):
            raise TypeError("datas must be a dict from bytes to bytes")
        for k, v in val.items():
            if not isinstance(k, bytes) or not isinstance(v, bytes):
                raise TypeError("datas must be a dict from bytes to bytes")
        self._datas = val

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        count = util.read_value(fd, 'I')
        util.log("count: {}", count)
        datas = {}
        for i in range(count):
            signature, key, copy, _, entry_length = util.read_value(
                fd, '4s4sb3sI')
            start = fd.tell()
            data = fd.read(entry_length)
            padded_length = util.pad(entry_length, 4)
            if fd.tell() - start != padded_length:
                fd.seek(padded_length - entry_length, 1)

            datas[key] = data

            util.log(
                ("signature: {}, key: {}, copy: {}, entry_length: {}, " +
                 "padded_length: {}"),
                signature, key, copy, entry_length, padded_length)

        return cls(datas=datas)

    def data_length(self, header):
        return (
            4 +
            (16 * len(self.datas)) +
            sum(util.pad(len(x), 4) for x in self.datas.values())
        )

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'I', len(self.datas))
        for key, data in self.datas.items():
            util.write_value(
                fd, '4s4sb3sI', b'8BIM', key, 1, b'\0\0\0', len(data)
            )
            fd.write(data)
            fd.write(b'\0' * (util.pad(len(data), 4) - len(data)))
