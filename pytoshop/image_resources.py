# -*- coding: utf-8 -*-


"""
The `ImageResources` section.

Image resource blocks are the basic building unit of several file
formats, including Photoshop's native file format, JPEG, and
TIFF. Image resources are used to store non-pixel data associated with
images, such as pen tool paths.
"""


from __future__ import unicode_literals, absolute_import


import struct


import six


import numpy as np
import traitlets as t


from . import docs
from . import enums
from . import util


class _ImageResourceBlockMeta(type(t.HasTraits)):
    """
    A metaclass that builds a mapping of subclasses.
    """
    mapping = {}

    def __new__(cls, name, parents, dct):
        new_cls = type(t.HasTraits).__new__(cls, name, parents, dct)

        if 'resource_id' in dct and isinstance(dct['resource_id'], int):
            if dct['resource_id'] in cls.mapping:
                raise ValueError(
                    "Duplicate resource_id '{}'".format(
                        dct['resource_id']))
            cls.mapping[dct['resource_id']] = new_cls

        return new_cls


@six.add_metaclass(_ImageResourceBlockMeta)
class ImageResourceBlock(t.HasTraits):
    """
    Stores a single image resource block.

    ``pytoshop`` currently doesn't deeply parse image resource
    blocks.  The raw data is merely retained for round-tripping.
    """
    name = t.Unicode(
        default_value='',
        max=255,
        help="Name of image resource."
    )

    def length(self, header):
        data_length = self.data_length(header)
        length = (
            4 + 2 +
            util.pascal_string_length(self.name, 2) +
            4 + data_length
        )
        if data_length % 2 != 0:
            length += 1
        return length
    length.__doc__ = docs.length

    def total_length(self, header):
        return self.length(header)
    total_length.__doc__ = docs.total_length

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        signature = fd.read(4)
        if signature != b'8BIM':
            raise ValueError('Invalid image resource block signature')

        resource_id = util.read_value(fd, 'H')
        name = util.read_pascal_string(fd, 2)

        data_length = util.read_value(fd, 'I')

        util.log(
            "resource_id: {}, name: {}, data_length: {}",
            resource_id, name, data_length
        )

        new_cls = _ImageResourceBlockMeta.mapping.get(
            resource_id, GenericImageResourceBlock)
        start = fd.tell()
        result = new_cls.read_data(fd, resource_id, name, data_length, header)
        end = fd.tell()
        if end - start != data_length:
            raise ValueError("{} read the wrong amount".format(new_cls))

        if data_length % 2 != 0:
            fd.read(1)

        return result
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        fd.write(b'8BIM')
        util.write_value(fd, 'H', self.resource_id)
        util.write_pascal_string(fd, self.name, 2)
        length = self.data_length(header)
        util.write_value(fd, 'I', length)
        start = fd.tell()
        self.write_data(fd, header)
        end = fd.tell()
        if end - start != length:
            raise ValueError(
                "{} wrote the wrong amount".format(self.__class__))
        if length % 2 != 0:
            fd.write(b'\0')
    write.__doc__ = docs.write


class GenericImageResourceBlock(ImageResourceBlock):
    resource_id = t.Int(
        help="Type of image resource."
    )
    data = t.Bytes(
        max=(1 << 32),
        help="Raw data of image resource."
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        data = fd.read(length)
        return cls(resource_id=resource_id, name=name, data=data)

    def data_length(self, header):
        return len(self.data)

    @util.trace_write
    def write_data(self, fd, header):
        fd.write(self.data)


class ImageResourceUnicodeString(ImageResourceBlock):
    value = t.Unicode(
        help="Value"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        data = fd.read(length)
        value = util.decode_unicode_string(data)
        return cls(
            name=name, value=value
        )

    def data_length(self, header):
        return util.unicode_string_length(self.value)

    @util.trace_write
    def write_data(self, fd, header):
        fd.write(util.encode_unicode_string(self.value))


class LayersGroupInfo(ImageResourceBlock):
    """
    Layers group information.

    Indicates which layers are locked together.
    """
    resource_id = enums.ImageResourceID.layers_group_info
    group_ids = t.List(
        t.Int,
        help="Layer group ids"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        data = fd.read(length)
        group_ids = np.frombuffer(data, '>u2').tolist()
        return cls(name=name, group_ids=group_ids)

    def data_length(self, header):
        return len(self.group_ids * 2)

    @util.trace_write
    def write_data(self, fd, header):
        data = np.array(self.group_ids, '>u2').tobytes()
        fd.write(data)


class BorderInfo(ImageResourceBlock):
    """
    Border information.
    """
    resource_id = enums.ImageResourceID.border_info
    border_width_num = t.Int(
        min=0, max=65535,
        help="Border width numerator"
    )
    border_width_den = t.Int(
        min=0, max=65535,
        help="Border width denominator")
    unit = t.Enum(
        list(enums.Units),
        default_value=enums.Units.inches,
        help="Unit. See `enums.Units`."
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        num, den, unit = struct.unpack('>HHH', fd.read(6))
        return cls(
            name=name, border_width_num=num, border_width_den=den,
            unit=unit)

    def data_length(self, header):
        return 6

    @util.trace_write
    def write_data(self, fd, header):
        data = struct.pack('>HHH', self.border_width_num,
                           self.border_width_den, self.unit)
        fd.write(data)


class BackgroundColor(ImageResourceBlock):
    """
    Background color.
    """
    resource_id = enums.ImageResourceID.background_color
    color_space = t.Enum(
        list(enums.ColorSpace),
        default_value=enums.ColorSpace.rgb,
        help="The color space. See `enums.ColorSpace`"
    )
    color = t.List(
        t.Int(min=-32767, max=65536), min=1, max=4,
        help="The color data.  If the color data does not require 4 "
        "values, the extra values are undefined and should be included "
        "as zeros."
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        space_id, a, b, c, d = struct.unpack('>HHHHH', fd.read(10))
        if space_id == enums.ColorSpace.lab:
            b -= 32767
            c -= 32767
        return cls(
            name=name, color_space=space_id, color=[a, b, c, d]
        )

    def data_length(self, header):
        return 10

    @util.trace_write
    def write_data(self, fd, header):
        color = self.color[:]
        color.extend([0] * (4 - len(color)))
        a, b, c, d = color
        if self.color_space == enums.ColorSpace.lab:
            b += 32767
            c += 32767
        data = struct.pack(
            '>HHHHH', self.color_space, a, b, c, d
        )
        fd.write(data)


class PrintFlags(ImageResourceBlock):
    """
    Print flags.
    """
    resource_id = enums.ImageResourceID.print_flags
    labels = t.Bool(
        help="labels"
    )
    crop_marks = t.Bool(
        help="crop marks"
    )
    color_bars = t.Bool(
        help="color bars"
    )
    registration_marks = t.Bool(
        help="registration marks"
    )
    negative = t.Bool(
        help="negative"
    )
    flip = t.Bool(
        help="flip"
    )
    interpolate = t.Bool(
        help="interpolate"
    )
    caption = t.Bool(
        help="caption"
    )
    print_flags = t.Bool(
        help="print flags"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        vals = struct.unpack('>BBBBBBBBB', fd.read(9))
        vals = [bool(x) for x in vals]
        return cls(
            name=name, labels=vals[0], crop_marks=vals[1],
            color_bars=vals[2], registration_marks=vals[3],
            negative=vals[4], flip=vals[5], interpolate=vals[6],
            caption=vals[7], print_flags=vals[8]
        )

    def data_length(self, header):
        return 9

    @util.trace_write
    def write_data(self, fd, header):
        vals = [
            self.labels, self.crop_marks, self.color_bars,
            self.registration_marks, self.negative, self.flip,
            self.interpolate, self.caption, self.print_flags
        ]
        vals = [(x and 255 or 0) for x in vals]
        data = struct.pack('>BBBBBBBBB', *vals)
        fd.write(data)


class GuideResourceBlock(t.HasTraits):
    location = t.Int(
        help="Location of guide in document coordinates."
    )
    direction = t.Enum(
        list(enums.GuideDirection),
        default_value=enums.Units.inches,
        help="Guide direction. See `enums.GuideDirection`."
    )

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        data = fd.read(5)
        location, direction = struct.unpack('>IB', data)
        return cls(location=location, direction=direction)

    @util.trace_write
    def write(self, fd, header):
        data = struct.pack('>IB', self.location, self.direction)
        fd.write(data)


class GridAndGuidesInfo(ImageResourceBlock):
    """
    Grid and guides resource.
    """
    resource_id = enums.ImageResourceID.grid_and_guides_info
    version = 1
    grid_hori = t.Int(
        help="Document-specific grid (horizontal). In 1/32 pt."
    )
    grid_vert = t.Int(
        help="Document-specific grid (vertical). In 1/32 pt."
    )
    guides = t.List(
        t.Instance(GuideResourceBlock),
        help="Guides.  See `GuideResourceBlock`."
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        version, grid_hori, grid_vert, nguides = struct.unpack(
            '>IIII', fd.read(16))
        if version != 1:
            raise ValueError(
                "Unknown version {} in grid and guides info block.".format(
                    version))
        guides = []
        for i in range(nguides):
            guides.append(GuideResourceBlock.read(fd, header))
        return cls(
            name=name, grid_hori=grid_hori, grid_vert=grid_vert,
            guides=guides
        )

    def data_length(self, header):
        return 16 + (5 * len(self.guides))

    @util.trace_write
    def write_data(self, fd, header):
        data = struct.pack(
            '>IIII', 1, self.grid_hori, self.grid_vert, len(self.guides)
        )
        fd.write(data)
        for guide in self.guides:
            guide.write(fd, header)


class CopyrightFlag(ImageResourceBlock):
    resource_id = enums.ImageResourceID.copyright_flag
    copyright = t.Bool(
        help="Is copyrighted?"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        copyright = bool(util.read_value(fd, 'B'))
        return cls(
            name=name, copyright=copyright
        )

    def data_length(self, header):
        return 1

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'B', self.copyright and 255 or 0)


class Url(ImageResourceBlock):
    resource_id = enums.ImageResourceID.url
    url = t.Bytes(
        help='URL'
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        url = fd.read(length)
        return cls(
            name=name, url=url
        )

    def data_length(self, header):
        return len(self.url)

    @util.trace_write
    def write_data(self, fd, header):
        fd.write(self.url)


class GlobalAngle(ImageResourceBlock):
    resource_id = enums.ImageResourceID.global_angle
    angle = t.Int(
        min=-360, max=360,
        help="Global light angle for the effect layer"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        angle = util.read_value(fd, 'i')
        return cls(
            name=name, angle=angle
        )

    def data_length(self, header):
        return 4

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'i', self.angle)


class EffectsVisible(ImageResourceBlock):
    resource_id = enums.ImageResourceID.effects_visible
    visible = t.Bool(
        help="Are effects visible?"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        visible = bool(util.read_value(fd, 'B'))
        return cls(
            name=name, visible=visible
        )

    def data_length(self, header):
        return 1

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'B', self.visible and 255 or 0)


class DocumentSpecificIdsSeedNumber(ImageResourceBlock):
    resource_id = enums.ImageResourceID.document_specific_ids_seed_number
    base_value = t.Int(
        help="Base value"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        base_value = bool(util.read_value(fd, 'I'))
        return cls(
            name=name, base_value=base_value
        )

    def data_length(self, header):
        return 4

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'I', self.base_value)


class UnicodeAlphaNames(ImageResourceUnicodeString):
    resource_id = enums.ImageResourceID.unicode_alpha_names


class GlobalAltitude(ImageResourceBlock):
    resource_id = enums.ImageResourceID.global_altitude
    altitude = t.Int(
        help="Global altitude"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        altitude = util.read_value(fd, 'I')
        return cls(
            name=name, altitude=altitude
        )

    def data_length(self, header):
        return 4

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'I', self.altitude)


class WorkflowUrl(ImageResourceUnicodeString):
    resource_id = enums.ImageResourceID.workflow_url


class AlphaIdentifiers(ImageResourceBlock):
    resource_id = enums.ImageResourceID.alpha_identifiers
    identifiers = t.List(
        t.Int,
        help="Alpha indentifiers"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        length = util.read_value(fd, 'I')
        identifiers = []
        for i in range(length):
            identifiers.append(util.read_value(fd, 'I'))
        return cls(
            name=name, identifiers=identifiers
        )

    def data_length(self, header):
        return 4 + (len(self.identifiers) * 4)

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'I', len(self.identifiers))
        for identifier in self.identifiers:
            util.write_value(fd, 'I', identifier)


class VersionInfo(ImageResourceBlock):
    resource_id = enums.ImageResourceID.version_info
    version = t.Int(
        help="version"
    )
    has_real_merged_data = t.Bool(
        help="has real merged data?"
    )
    writer = t.Unicode(
        help="writer name"
    )
    reader = t.Unicode(
        help="reader name"
    )
    file_version = t.Int(
        help="file version"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        version = util.read_value(fd, 'I')
        has_real_merged_data = bool(util.read_value(fd, 'B'))
        writer = util.read_unicode_string(fd)
        reader = util.read_unicode_string(fd)
        file_version = util.read_value(fd, 'I')
        return cls(
            name=name, version=version,
            has_real_merged_data=has_real_merged_data, writer=writer,
            reader=reader, file_version=file_version
        )

    def data_length(self, header):
        return (
            4 + 1 +
            util.unicode_string_length(self.writer) +
            util.unicode_string_length(self.reader) +
            4)

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'I', self.version)
        util.write_value(fd, 'B', self.has_real_merged_data)
        util.write_unicode_string(fd, self.writer)
        util.write_unicode_string(fd, self.reader)
        util.write_value(fd, 'I', self.file_version)


class PrintScale(ImageResourceBlock):
    resource_id = enums.ImageResourceID.print_scale
    style = t.Enum(
        list(enums.PrintScaleStyle),
        default_value=enums.PrintScaleStyle.centered,
        help="style"
    )
    x = t.Float(
        help="x location"
    )
    y = t.Float(
        help="y location"
    )
    scale = t.Float(
        help="scale"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        style = util.read_value(fd, 'H')
        x = util.read_value(fd, 'f')
        y = util.read_value(fd, 'f')
        scale = util.read_value(fd, 'f')
        return cls(
            name=name, style=style, x=x, y=y, scale=scale
        )

    def data_length(self, header):
        return (2 + 4 + 4 + 4)

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'H', self.style)
        util.write_value(fd, 'f', self.x)
        util.write_value(fd, 'f', self.y)
        util.write_value(fd, 'f', self.scale)


class ImageResources(t.HasTraits):
    """
    The image resource block section.
    """
    blocks = t.List(
        t.Instance(ImageResourceBlock),
        help="List of all `ImageResourceBlock` items."
    )

    def length(self, header):
        return sum(block.total_length(header) for block in self.blocks)
    length.__doc__ = docs.length

    def total_length(self, header):
        return 4 + self.length(header)
    total_length.__doc__ = docs.total_length

    def get_block(self, resource_id):
        """
        Get the first block with the given resource id.
        """
        for block in self.blocks:
            if block.resource_id == resource_id:
                return block
        return None

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        length = util.read_value(fd, 'I')
        end = fd.tell() + length

        util.log("length: {}, end: {}", length, end)

        blocks = []
        while fd.tell() < end:
            blocks.append(ImageResourceBlock.read(fd, header))

        if fd.tell() != end:
            raise ValueError(
                "read the wrong amount reading image resource blocks")

        return cls(blocks=blocks)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'I', self.length(header))
        for block in self.blocks:
            block.write(fd, header)
    write.__doc__ = docs.write
