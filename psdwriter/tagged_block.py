# -*- coding: utf-8 -*-


"""
`TaggedBlock` objects.
"""


import traitlets as t


from . import docs
from . import enums
from . import path
from . import util


class _TaggedBlockMeta(type(t.HasTraits)):
    """
    A metaclass that builds a mapping of subclasses.
    """
    mapping = {}

    def __new__(cls, name, parents, dct):
        new_cls = super().__new__(cls, name, parents, dct)

        if 'code' in dct and isinstance(dct['code'], bytes):
            if dct['code'] in cls.mapping:
                raise ValueError("Duplicate code '{}'".format(dct['code']))
            cls.mapping[dct['code']] = new_cls

        return new_cls


class TaggedBlock(t.HasTraits, metaclass=_TaggedBlockMeta):
    _large_layer_info_codes = set([
        b'LMsk', b'Lr16', b'Lr32', b'Layr', b'Mt16', b'Mt32',
        b'Mtrn', b'Alph', b'FMsk', b'Ink2', b'FEid', b'FXid',
        b'PxSD'])

    def length(self, header):
        return self.data_length(header)
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
                "{} wrote the wrong amount".format(self.__class__))
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
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        data = fd.read(length)
        return cls(code=code, data=data)

    def data_length(self, header):
        return len(self.data)

    @util.trace_write
    def write_data(self, fd, header):
        fd.write(self.data)


class UnicodeLayerName(TaggedBlock):
    code = b'luni'
    name = t.Unicode(
        help="The name of the layer."
    )

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
    code = b'lyid'
    id = t.Int(
        help="Layer id"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        id = util.read_value(fd, 'I')
        return cls(id=id)

    def data_length(self, header):
        return 4

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'I', self.id)


class LayerNameSource(TaggedBlock):
    code = b'lnsr'
    id = t.Int(
        help="The layer id of the source of the name of this layer"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        id = util.read_value(fd, 'I')
        return cls(id=id)

    def data_length(self, header):
        return 4

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'I', self.id)


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
    code = b'lsct'


class NestedSectionDividerSetting(_SectionDividerSetting):
    code = b'lsdk'


class VectorMask(TaggedBlock):
    code = b'vmsk'
    version = t.Int(
        3,
        help='Vector mask block version'
    )
    invert = t.Bool(
        help='Invert mask'
    )
    not_link = t.Bool(
        help="Don't link mask"
    )
    disable = t.Bool(
        help="Disable mask"
    )
    path_resource = t.Instance(
        path.PathResource,
        help="`path.PathResource` instance`"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        version = util.read_value(fd, 'I')
        flags = util.read_value(fd, 'I')
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
        util.write_value(fd, 'I', self.version)

        flags = util.pack_bitflags(self.invert, self.not_link, self.disable)

        util.write_value(fd, 'I', flags)

        self.path_resource.write(fd, header)
