# -*- coding: utf-8 -*-


"""
`TaggedBlock` objects.
"""


import struct


import traitlets as t


from . import docs
from . import enums
from . import util


class _TaggedBlockMeta(type(t.HasTraits)):
    """
    A mtaclass that builds a mapping of subclasses.
    """
    mapping = {}

    def __new__(cls, name, parents, dct):
        new_cls = super().__new__(cls, name, parents, dct)

        if 'code' in dct and isinstance(dct['code'], bytes):
            cls.mapping[dct['code']] = new_cls

        return new_cls


class TaggedBlock(t.HasTraits, metaclass=_TaggedBlockMeta):
    _large_layer_info_codes = set([
        b'LMsk', b'Lr16', b'Lr32', b'Layr', b'Mt16', b'Mt32',
        b'Mtrn', b'Alph', b'FMsk', b'Ink2', b'FEid', b'FXid',
        b'PxSD'])

    def length(self, header):
        return len(self.data)
    length.__doc__ = docs.length

    def total_length(self, header, padding=1):
        length = 8
        if header.version == 2 and self.code in self._large_layer_info_codes:
            length += 8
        else:
            length += 4
        length += util.pad(self.length(header), padding)
        return length
    total_length.__doc__ = docs.total_length

    @classmethod
    @util.trace_read
    def read(cls, fd, header, padding=1):
        signature = fd.read(4)
        if signature not in (b'8BIM', b'8B64'):
            raise ValueError('Invalid signature in tagged block')

        code = fd.read(4)

        if header.version == 2 and code in cls._large_layer_info_codes:
            length = util.read_value(fd, 'Q')
        else:
            length = util.read_value(fd, 'I')
        padded_length = util.pad(length, padding)

        util.log(
            "code: {}, length: {}, padded_length: {}",
            code, length, padded_length
        )

        new_cls = _TaggedBlockMeta.mapping.get(code, GenericTaggedBlock)
        data = fd.read(length)
        fd.seek(padded_length - length, 1)

        return new_cls.read(code, data)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header, padding=1):
        if header.version == 2 and self.code in self._large_layer_info_codes:
            fd.write(b'8B64')
        else:
            fd.write(b'8BIM')
        fd.write(self.code)
        length = len(self.data)
        padded_length = util.pad(length, padding)
        if header.version == 2 and self.code in self._large_layer_info_codes:
            util.write_value(fd, 'Q', length)
        else:
            util.write_value(fd, 'I', length)
        fd.write(self.data)
        fd.write(b'\0' * (padded_length - length))
    write.__doc__ = docs.write


class GenericTaggedBlock(TaggedBlock):
    """
    A generic `TaggedBlock` subclass for tag codes ``psdwriter``
    doesn't know about.
    """

    code = t.Bytes(
        min=4, max=4,
        help="The 4-letter tagged block code"
    )
    data = t.Bytes(
        b'',
        help="The raw data for the block"
    )

    @classmethod
    def read(cls, code, data):
        return cls(code=code, data=data)
    read.__func__.__doc__ = docs.read


class UnicodeLayerName(TaggedBlock):
    code = b'luni'
    name = t.Unicode(
        help="The name of the layer."
    )

    @property
    def data(self):
        return util.encode_unicode_string(self.name)

    @classmethod
    def read(cls, code, data):
        name = util.decode_unicode_string(data)
        util.log('name: {}', name)
        return cls(name=name)
    read.__func__.__doc__ = docs.read


class LayerId(TaggedBlock):
    code = b'lyid'
    id = t.Int(
        help="Layer id"
    )

    @property
    def data(self):
        return struct.pack('>I', self.id)

    @classmethod
    def read(cls, code, data):
        id, = struct.unpack('>I', data)
        util.log('id: {}', id)
        return cls(id=id)
    read.__func__.__doc__ = docs.read


class LayerNameSource(TaggedBlock):
    code = b'lnsr'
    id = t.Int(
        help="The layer id of the source of the name of this layer"
    )

    @property
    def data(self):
        return struct.pack('>I', self.id)

    @classmethod
    def read(cls, code, data):
        id, = struct.unpack('>I', data)
        util.log('id: {}', id)
        return cls(id=id)
    read.__func__.__doc__ = docs.read


class _SectionDividerSetting(TaggedBlock):
    type = t.Enum(
        list(enums.SectionDividerSetting),
        default_value=enums.SectionDividerSetting.open,
        help="Section divider type. See `enums.SectionDividerSetting`."
    )
    key = t.Enum(
        list(enums.BlendMode), allow_none=True,
        help="Section divider key"
    )
    subtype = t.Bool(
        None, allow_none=True,
        help="Section divider subtype. False=normal, True=Scene group, "
        "affects the animation timeline"
    )

    @property
    def data(self):
        data = struct.pack('>I', self.type)
        if self.key is not None or self.subtype is not None:
            if self.key is None:
                key = b'norm'
            else:
                key = self.key
            data += b'8BIM' + key
            if self.subtype is not None:
                data += struct.pack('>I', self.subtype)
        return data

    @classmethod
    def read(cls, code, data):
        type, = struct.unpack('>I', data[:4])

        key = None
        subtype = None
        if len(data) >= 12:
            key = data[8:12]

            if len(data) >= 16:
                subtype = bool(struct.unpack('>I', data[12:16])[0])

        util.log('type: {}, key: {}, subtype: {}', type, key, subtype)

        return cls(type=type, key=key, subtype=subtype)
    read.__func__.__doc__ = docs.read


class SectionDividerSetting(_SectionDividerSetting):
    code = b'lsct'


class NestedSectionDividerSetting(_SectionDividerSetting):
    code = b'lsdk'
