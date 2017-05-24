# -*- coding: utf-8 -*-


"""
`TaggedBlock` objects.
"""


from __future__ import unicode_literals, absolute_import


import io
import struct


import six


from . import actions
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
            if (not isinstance(k, bytes) or
                not isinstance(v, tuple) or
                len(v) != 2 or
                not isinstance(v[0], bool) or
                not isinstance(v[1], bytes)):
                raise TypeError(
                    "datas must be a dict from bytes to (bool, bytes)")
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
            copy = bool(copy)
            padded_length = util.pad(entry_length, 4)
            if fd.tell() - start != padded_length:
                fd.seek(padded_length - entry_length, 1)

            datas[key] = (copy, data)

            util.log(
                ("signature: {}, key: {}, copy: {}, entry_length: {}, " +
                 "padded_length: {}"),
                signature, key, copy, entry_length, padded_length)

        return cls(datas=datas)

    def data_length(self, header):
        return (
            4 +
            (16 * len(self.datas)) +
            sum(util.pad(len(x[1]), 4) for x in self.datas.values())
        )

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'I', len(self.datas))
        for key, (copy, data) in self.datas.items():
            util.write_value(
                fd, '4s4sb3sI', b'8BIM', key, copy, b'\0\0\0', len(data)
            )
            fd.write(data)
            fd.write(b'\0' * (util.pad(len(data), 4) - len(data)))


class LinkedLayer(object):
    def __init__(self,
                 link_type=b'liFD',
                 version=7,
                 unique_id=b'',
                 filename='',
                 filetype=b'8BPB',
                 creator=b'8BIM',
                 content=None,
                 embedded_file=None,
                 uuid=''):
        if content is not None and embedded_file is not None:
            raise ValueError(
                "May not provide both content and embedded_file"
            )

        self.link_type = link_type
        self.version = version
        self.unique_id = unique_id
        self.filename = filename
        self.filetype = filetype
        self.creator = creator
        self.content = content
        self.uuid = uuid
        self.embedded_file = embedded_file

    @property
    def link_type(self):
        return self._link_type

    @link_type.setter
    def link_type(self, value):
        if (not isinstance(value, bytes) or len(value) != 4 or
                value not in (b'liFD', b'liFE', b'liFA')):
            raise ValueError("Invalid link type '{}'".format(repr(value)))
        self._link_type = value

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, value):
        if (not isinstance(value, int) or
                value < 1 or value > 7):
            raise ValueError("version must be 1 - 7")
        self._version = value

    @property
    def unique_id(self):
        return self._unique_id

    @unique_id.setter
    def unique_id(self, value):
        if not isinstance(value, six.text_type):
            raise TypeError("unique_id must be a unicode string")
        self._unique_id = value

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        if not isinstance(value, six.text_type):
            raise TypeError("filename must be a unicode string")
        self._filename = value

    @property
    def filetype(self):
        return self._filetype

    @filetype.setter
    def filetype(self, value):
        if (not isinstance(value, bytes) or len(value) != 4):
            raise ValueError("Invalid filetype '{}'".format(repr(value)))
        self._filetype = value

    @property
    def creator(self):
        return self._creator

    @creator.setter
    def creator(self, value):
        if (not isinstance(value, bytes) or len(value) != 4):
            raise ValueError("Invalid creator '{}'".format(repr(value)))
        self._creator = value

    @property
    def content(self):
        if self._content is not None:
            return self._content
        else:
            fd = io.BytesIO()
            self.embedded_file.write(fd)
            return fd.getvalue()

    @content.setter
    def content(self, value):
        if value is None:
            self._content = value
        else:
            if not isinstance(value, bytes):
                raise ValueError("content must be bytes or None")
            self._content = value
            self._embedded_file = None

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        if (value is not None and not isinstance(value, six.text_type)):
            raise ValueError("uuid must be a unicode string")
        self._uuid = value

    @property
    def embedded_file(self):
        if self._content is not None:
            from . import read
            if self._content.startswith(b'8BPS'):
                fd = io.BytesIO(self._content)
                psd = read(fd)
                return psd
            else:
                raise ValueError(
                    "Content is not an embedded Photoshop file. "
                    "Use self.content directly and decode using the "
                    "appropriate tool."
                )
        else:
            return self._embedded_file

    @embedded_file.setter
    def embedded_file(self, value):
        if value is None:
            self._embedded_file = value
        else:
            from . import core
            if value is not None and not isinstance(value, core.PsdFile):
                raise TypeError(
                    "embedded_file must be a PsdFile instance or None"
                )
            self._embedded_file = value
            self._content = None

    @classmethod
    @util.trace_read
    def read(cls, fd):
        entry_start = fd.tell()
        entry_length = util.read_value(fd, 'Q')
        link_type = fd.read(4)
        version = util.read_value(fd, 'I')
        unique_id = util.read_pascal_string(fd)
        original_file_name = util.read_unicode_string(fd)
        filetype = fd.read(4)
        creator = fd.read(4)
        file_length = util.read_value(fd, 'Q')
        have_file_open_descriptor = util.read_value(fd, 'B')
        if have_file_open_descriptor:
            util.read_value(fd, 'I')
            actions.Descriptor.read(fd)

        # TODO: Use an embedded file descriptor to avoid reading
        # whole thing into memory
        content = fd.read(file_length)

        if version == 5:
            uuid = util.read_unicode_string(fd)
        else:
            uuid = None

        util.log(
            "link_type: {}, version: {}, unique_id: {}, "
            "filename: {}, filetype: {}, creator: {}, "
            "file_length: {}, have_file_open_descriptor: {} "
            "len(content): {}, content: {}, uuid: {}",
            link_type, version, unique_id, original_file_name,
            filetype, creator, file_length, have_file_open_descriptor,
            len(content), content[:8], uuid
        )

        fd.seek(entry_start + 8 + entry_length)

        with open("foo.psb", "wb") as fd:
            fd.write(content)

        return cls(
            link_type=link_type,
            version=version,
            unique_id=unique_id,
            filename=original_file_name,
            filetype=filetype,
            creator=creator,
            content=content,
            uuid=uuid
        )

    @util.trace_write
    def write(self, fd):
        content = self.content
        start = fd.tell()
        fd.seek(8, 1)
        fd.write(self.link_type)
        util.write_value(fd, 'I', self.version)
        util.write_pascal_string(fd, self.unique_id)
        util.write_unicode_string(fd, self.filename)
        fd.write(self.filetype)
        fd.write(self.creator)
        util.write_value(fd, 'Q', len(content))
        util.write_value(fd, 'B', 1)
        util.write_value(fd, 'I', 16)
        descr = actions.Descriptor(items=[
            (b'compInfo', actions.Descriptor(items=[
                (b'compID', actions.Integer(-1)),
                (b'originalCompID', actions.Integer(-1))
                ])
            )])
        descr.write(fd)
        fd.write(content)

        if self.version == 5:
            util.write_unicode_string(fd, self.uuid)
        end = fd.tell()
        fd.seek(start)
        util.write_value(fd, 'Q', (end - start) - 8)
        fd.seek(end)


class LinkedLayers(TaggedBlock):
    def __init__(self, layers=None):
        if layers is None:
            layers = []
        self.layers = layers

    _code = b'lnkD'

    @property
    def layers(self):
        return self._layers

    @layers.setter
    def layers(self, value):
        util.assert_is_list_of(value, LinkedLayer)
        self._layers = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        layers = []

        start = fd.tell()
        end = start + length
        while fd.tell() < end:
            layer = LinkedLayer.read(fd)
            layers.append(layer)
            pad = -(fd.tell() - start) % 4
            fd.seek(pad, 1)

        return cls(layers=layers)

    @util.trace_write
    def write(self, fd, header, padding=1):
        fd.write(b'8BIM')
        fd.write(self.code)

        length_pos = fd.tell()
        if header.version == 2:
            fd.seek(8, 1)
        else:
            fd.seek(4, 1)

        start = fd.tell()
        for layer in self.layers:
            layer.write(fd)
            pad = -(fd.tell() - start) % 4
            fd.write(b'\0' * pad)
        end = fd.tell()

        fd.seek(length_pos)
        if header.version == 2:
            util.write_value(fd, 'Q', end - start)
        else:
            util.write_value(fd, 'I', end - start)
        fd.seek(end)


class LinkedLayers2(LinkedLayers):
    _code = b'lnk2'


class LinkedLayers3(LinkedLayers):
    _code = b'lnk3'


class PlacedLayer(TaggedBlock):
    def __init__(self,
                 unique_id=b'',
                 page_number=1,
                 total_pages=1,
                 antialias_policy=16,
                 placed_layer_type=enums.PlacedLayerType.unknown,
                 transform=None):
        self.unique_id = unique_id
        self.page_number = page_number
        self.total_pages = total_pages
        self.antialias_policy = antialias_policy
        self.placed_layer_type = placed_layer_type
        if transform is None:
            transform = [0.0] * 8
        self.transform = transform

    _code = b'PlLd'

    @property
    def unique_id(self):
        return self._unique_id

    @unique_id.setter
    def unique_id(self, value):
        if not isinstance(value, six.text_type):
            raise TypeError("unique_id must be a unicode string")
        self._unique_id = value

    @property
    def page_number(self):
        return self._page_number

    @page_number.setter
    def page_number(self, value):
        if not isinstance(value, int) or value < 1:
            raise ValueError("page_number must be a positive integer")
        self._page_number = value

    @property
    def total_pages(self):
        return self._total_pages

    @total_pages.setter
    def total_pages(self, value):
        if not isinstance(value, int) or value < 1:
            raise ValueError("total_pages must be a positive integer")
        self._total_pages = value

    @property
    def antialias_policy(self):
        return self._antialias_policy

    @antialias_policy.setter
    def antialias_policy(self, value):
        if not isinstance(value, int) or value < 0:
            raise ValueError("antialias_policy must be a non-negative integer")
        self._antialias_policy = value

    @property
    def placed_layer_type(self):
        return self._placed_layer_type

    @placed_layer_type.setter
    def placed_layer_type(self, value):
        if value not in list(enums.PlacedLayerType):
            raise ValueError("Invalid placed layer type.")
        self._placed_layer_type = value

    @property
    def transform(self):
        return self._transform

    @transform.setter
    def transform(self, value):
        util.assert_is_list_of(value, float)
        if len(value) != 8:
            raise ValueError("transform must have 8 values")
        self._transform = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        start = fd.tell()
        type = fd.read(4)
        if type != b'plcL':
            raise ValueError(
                "Invalid type '{}' for placed layer".format(type)
            )
        version = util.read_value(fd, 'I')
        if version != 3:
            raise ValueError(
                "Invalid version '{}' for placed layer".format(version)
            )
        unique_id = util.read_pascal_string(fd)
        page_number = util.read_value(fd, 'I')
        total_pages = util.read_value(fd, 'I')
        antialias_policy = util.read_value(fd, 'I')
        placed_layer_type = util.read_value(fd, 'I')
        transform = list(struct.unpack('>dddddddd', fd.read(8 * 8)))
        fd.seek(start + length)

        util.log(
            "unique_id: {}, page_number: {}, total_pages: {}, "
            "antialias_policy: {}, placed_layer_type: {}, "
            "transform: {}",
            unique_id, page_number, total_pages, antialias_policy,
            placed_layer_type, transform
        )

        return cls(
            unique_id=unique_id,
            page_number=page_number,
            total_pages=total_pages,
            antialias_policy=antialias_policy,
            placed_layer_type=placed_layer_type,
            transform=transform
        )

    def data_length(self, header):
        return (4 + 4 + util.pascal_string_length(self.unique_id) +
                4 + 4 + 4 + 4 + 8*8 + 4 + 4 + 4)

    @util.trace_write
    def write_data(self, fd, header):
        fd.write(b'plcL')
        util.write_value(fd, 'I', 3)
        util.write_pascal_string(fd, self.unique_id)
        util.write_value(fd, 'I', self.page_number)
        util.write_value(fd, 'I', self.total_pages)
        util.write_value(fd, 'I', self.antialias_policy)
        util.write_value(fd, 'I', self.placed_layer_type)
        fd.write(struct.pack('>dddddddd', *self.transform))
        util.write_value(fd, 'I', 0)
        util.write_value(fd, 'I', 0)
        util.write_value(fd, 'I', 0)


class PlacedLayerData(TaggedBlock):
    def __init__(self, descr=None):
        self.descr = descr

    _code = b'SoLd'

    @property
    def descr(self):
        return self._descr

    @descr.setter
    def descr(self, value):
        if not isinstance(value, actions.OSType):
            raise TypeError("descr must be an OSType instance")
        self._descr = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, code, length, header):
        start = fd.tell()

        identifier = fd.read(4)
        if identifier != b'soLD':
            raise ValueError(
                "Invalid identifier {} for placed layer data".format(
                    identifier)
            )

        version = util.read_value(fd, 'I')
        if version != 4:
            raise ValueError(
                "Invalid version {} for placed layer data".format(
                    version)
            )

        descriptor_version = util.read_value(fd, 'I')
        if descriptor_version != 16:
            raise ValueError(
                "Invalid descriptor version {} for placed layer data".format(
                    descriptor_version)
            )

        descr = actions.Descriptor.read(fd)

        fd.seek(-(fd.tell() - start) % 4, 1)

        return cls(descr=descr)

    def data_length(self, header):
        temp_fd = io.BytesIO()
        self.descr.write(temp_fd)
        length = temp_fd.tell()
        return 12 + length + (-length % 4)

    @util.trace_write
    def write_data(self, fd, header):
        start = fd.tell()
        fd.write(b'soLD')
        util.write_value(fd, 'I', 4)
        util.write_value(fd, 'I', 16)
        self.descr.write(fd)
        fd.write(b'\0' * (-(fd.tell() - start) % 4))
