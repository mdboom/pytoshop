# -*- coding: utf-8 -*-


"""
The `ImageResources` section.

Image resource blocks are the basic building unit of several file
formats, including Photoshop's native file format, JPEG, and
TIFF. Image resources are used to store non-pixel data associated with
images, such as pen tool paths.
"""


from __future__ import unicode_literals, absolute_import


import six


import numpy as np


from . import docs
from . import enums
from . import util


class _ImageResourceBlockMeta(type):
    """
    A metaclass that builds a mapping of subclasses.
    """
    mapping = {}

    def __new__(cls, name, parents, dct):
        new_cls = type.__new__(cls, name, parents, dct)

        if '_resource_id' in dct and isinstance(dct['_resource_id'], int):
            resource_id = dct['_resource_id']
            if resource_id in cls.mapping:
                raise ValueError(
                    "Duplicate resource_id '{}'".format(
                        resource_id))
            cls.mapping[resource_id] = new_cls

        return new_cls


@six.add_metaclass(_ImageResourceBlockMeta)
class ImageResourceBlock(object):
    """
    Stores a single image resource block.

    ``pytoshop`` currently doesn't deeply parse image resource
    blocks.  The raw data is merely retained for round-tripping.
    """
    @property
    def name(self):
        "Name of image resource."
        return self._name

    @name.setter
    def name(self, value):
        if isinstance(value, bytes):
            value = value.decode('ascii')

        if (not isinstance(value, six.text_type) or
                len(value) > 255):
            raise ValueError("name must be unicode string of length < 255")
        self._name = value

    @property
    def resource_id(self):
        "Type of image resource."
        return self._resource_id

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
    def __init__(self, name='', resource_id=0, data=b''):
        self.name = name
        self.resource_id = resource_id
        self.data = data

    @property
    def resource_id(self):
        "Type of image resource."
        return self._resource_id

    @resource_id.setter
    def resource_id(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 16)):
            raise ValueError(
                "resource_id must be a 16-bit positive integer"
            )
        self._resource_id = value

    @property
    def data(self):
        "Raw data of image resource."
        return self._data

    @data.setter
    def data(self, value):
        if (not isinstance(value, bytes) or
                len(value) > (1 << 32)):
            raise ValueError("data must be a byte string")
        self._data = value

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
    def __init__(self, name='', value=''):
        self.name = name
        self.value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if (not isinstance(value, six.text_type) or
                len(value) > (1 << 32)):
            raise TypeError("value must be a unicode string")
        self._value = value

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
    def __init__(self, name='', group_ids=[]):
        self.name = name
        self.group_ids = group_ids

    _resource_id = enums.ImageResourceID.layers_group_info

    @property
    def group_ids(self):
        return self._group_ids

    @group_ids.setter
    def group_ids(self, value):
        util.assert_is_list_of(value, int, min=0, max=65535)
        self._group_ids = value

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
    def __init__(self,
                 name='',
                 border_width_num=0,
                 border_width_den=1,
                 unit=enums.Units.inches):
        self.name = name
        self.border_width_num = border_width_num
        self.border_width_den = border_width_den
        self.unit = unit

    _resource_id = enums.ImageResourceID.border_info

    @property
    def border_width_num(self):
        "Border width numerator"
        return self._border_width_num

    @border_width_num.setter
    def border_width_num(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > 65535):
            raise ValueError(
                "border_width_num must be integer in range 0-65535"
            )
        self._border_width_num = value

    @property
    def border_width_den(self):
        "Border width denominator"
        return self._border_width_den

    @border_width_den.setter
    def border_width_den(self, value):
        if (not isinstance(value, int) or
                value < 1 or value > 65535):
            raise ValueError(
                "border_width_den must be integer in range 1-65535"
            )
        self._border_width_den = value

    @property
    def unit(self):
        "Unit. See `enums.Units`."
        return self._unit

    @unit.setter
    def unit(self, value):
        if value not in list(enums.Units):
            raise ValueError("Invalid unit.")
        self._unit = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        num, den, unit = util.read_value(fd, 'HHH')
        return cls(
            name=name, border_width_num=num, border_width_den=den,
            unit=unit)

    def data_length(self, header):
        return 6

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(
            fd, 'HHH', self.border_width_num,
            self.border_width_den, self.unit
        )


class BackgroundColor(ImageResourceBlock):
    """
    Background color.
    """
    def __init__(self,
                 name='',
                 color_space=enums.ColorSpace.rgb,
                 color=[]):
        self.name = name
        self.color_space = color_space
        self.color = color

    _resource_id = enums.ImageResourceID.background_color

    @property
    def color_space(self):
        "The color space. See `enums.ColorSpace`"
        return self._color_space

    @color_space.setter
    def color_space(self, value):
        if value not in list(enums.ColorSpace):
            raise ValueError("Invalid color space.")
        self._color_space = value

    @property
    def color(self):
        """
        The color data.  If the color data does not require 4 values,
        the extra values are undefined and should be included as
        zeros.
        """
        return self._color

    @color.setter
    def color(self, value):
        util.assert_is_list_of(value, int, -32767, 65536)
        if len(value) < 1 or len(value) > 4:
            raise ValueError("Color must be of length 1-4")
        self._color = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        space_id, a, b, c, d = util.read_value(fd, 'HHHHH')
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
        util.write_value(
            fd, 'HHHHH', self.color_space, a, b, c, d
        )


class PrintFlags(ImageResourceBlock):
    """
    Print flags.
    """
    def __init__(self,
                 name='',
                 labels=False,
                 crop_marks=False,
                 color_bars=False,
                 registration_marks=False,
                 negative=False,
                 flip=False,
                 interpolate=False,
                 caption=False,
                 print_flags=False):
        self.name = name
        self.labels = labels
        self.crop_marks = crop_marks
        self.color_bars = color_bars
        self.registration_marks = registration_marks
        self.negative = negative
        self.flip = flip
        self.interpolate = interpolate
        self.caption = caption
        self.print_flags = print_flags

    _resource_id = enums.ImageResourceID.print_flags

    @property
    def labels(self):
        "labels"
        return self._labels

    @labels.setter
    def labels(self, value):
        self._labels = bool(value)

    @property
    def crop_marks(self):
        "crop marks"
        return self._crop_marks

    @crop_marks.setter
    def crop_marks(self, value):
        self._crop_marks = bool(value)

    @property
    def color_bars(self):
        "color bars"
        return self._color_bars

    @color_bars.setter
    def color_bars(self, value):
        self._color_bars = bool(value)

    @property
    def registration_marks(self):
        "registration marks"
        return self._registration_marks

    @registration_marks.setter
    def registration_marks(self, value):
        self._registration_marks = bool(value)

    @property
    def negative(self):
        "negative"
        return self._negative

    @negative.setter
    def negative(self, value):
        self._negative = bool(value)

    @property
    def flip(self):
        "flip"
        return self._flip

    @flip.setter
    def flip(self, value):
        self._flip = bool(value)

    @property
    def interpolate(self):
        "interpolate"
        return self._interpolate

    @interpolate.setter
    def interpolate(self, value):
        self._interpolate = bool(value)

    @property
    def caption(self):
        "caption"
        return self._caption

    @caption.setter
    def caption(self, value):
        self._caption = bool(value)

    @property
    def print_flags(self):
        "print flags"
        return self._print_flags

    @print_flags.setter
    def print_flags(self, value):
        self._print_flags = bool(value)

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        vals = util.read_value(fd, 'BBBBBBBBB')
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
        util.write_value(fd, 'BBBBBBBBB', *vals)


class GuideResourceBlock(object):
    def __init__(self, location=0, direction=enums.GuideDirection.vertical):
        self.location = location
        self.direction = direction

    @property
    def location(self):
        "Location of guide in document coordinates."
        return self._location

    @location.setter
    def location(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("location must be a 32-bit unsigned int")
        self._location = value

    @property
    def direction(self):
        "Guide direction. See `enums.GuideDirection`."
        return self._direction

    @direction.setter
    def direction(self, value):
        if value not in list(enums.GuideDirection):
            raise ValueError("Invalid guide direction")
        self._direction = value

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        location, direction = util.read_value(fd, 'IB')
        return cls(location=location, direction=direction)

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'IB', self.location, self.direction)


class GridAndGuidesInfo(ImageResourceBlock):
    """
    Grid and guides resource.
    """
    def __init__(self,
                 name='',
                 grid_hori=0,
                 grid_vert=0,
                 guides=[]):
        self.name = name
        self.grid_hori = grid_hori
        self.grid_vert = grid_vert
        self.guides = guides

    _resource_id = enums.ImageResourceID.grid_and_guides_info

    @property
    def version(self):
        return 1

    @property
    def grid_hori(self):
        "Document-specific grid (horizontal). In 1/32 pt."
        return self._grid_hori

    @grid_hori.setter
    def grid_hori(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("grid_hori must be a 32-bit unsigned int")
        self._grid_hori = value

    @property
    def grid_vert(self):
        "Document-specific grid (vertical). In 1/32 pt."
        return self._grid_vert

    @grid_vert.setter
    def grid_vert(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("grid_vert must be a 32-bit unsigned int")
        self._grid_vert = value

    @property
    def guides(self):
        "Guides.  See `GuideResourceBlock`."
        return self._guides

    @guides.setter
    def guides(self, value):
        util.assert_is_list_of(value, GuideResourceBlock)
        self._guides = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        version, grid_hori, grid_vert, nguides = util.read_value(
            fd, 'IIII')
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
        util.write_value(
            fd, 'IIII', 1, self.grid_hori, self.grid_vert, len(self.guides)
        )
        for guide in self.guides:
            guide.write(fd, header)


class CopyrightFlag(ImageResourceBlock):
    def __init__(self, name='', copyright=False):
        self.name = name
        self.copyright = copyright

    _resource_id = enums.ImageResourceID.copyright_flag

    @property
    def copyright(self):
        "Is copyrighted?"
        return self._copyright

    @copyright.setter
    def copyright(self, value):
        self._copyright = bool(value)

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
    def __init__(self, name='', url=b''):
        self.name = name
        self.url = url

    _resource_id = enums.ImageResourceID.url

    @property
    def url(self):
        "URL"
        return self._url

    @url.setter
    def url(self, value):
        if not isinstance(value, bytes):
            raise TypeError("url must be bytes string")
        self._url = value

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
    def __init__(self, name='', angle=0):
        self.name = name
        self.angle = angle

    _resource_id = enums.ImageResourceID.global_angle

    @property
    def angle(self):
        "Global light angle for the effect layer"
        return self._angle

    @angle.setter
    def angle(self, value):
        if (not isinstance(value, int) or
                value < -360 or value > 360):
            raise ValueError(
                "angle must be an int in range -360 to 360"
            )
        self._angle = value

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
    def __init__(self, name='', visible=False):
        self.name = name
        self.visible = visible

    _resource_id = enums.ImageResourceID.effects_visible

    @property
    def visible(self):
        "Are effects visible?"
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = bool(value)

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
    def __init__(self, name='', base_value=0):
        self.name = name
        self.base_value = base_value

    _resource_id = enums.ImageResourceID.document_specific_ids_seed_number

    @property
    def base_value(self):
        "Base value"
        return self._base_value

    @base_value.setter
    def base_value(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("base_value must be a 32-bit integer")
        self._base_value = value

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
    _resource_id = enums.ImageResourceID.unicode_alpha_names


class GlobalAltitude(ImageResourceBlock):
    def __init__(self, name='', altitude=0):
        self.name = name
        self.altitude = altitude

    _resource_id = enums.ImageResourceID.global_altitude

    @property
    def altitude(self):
        "Global altitude"
        return self._altitude

    @altitude.setter
    def altitude(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("altitude must be a 32-bit integer")
        self._altitude = value

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
    _resource_id = enums.ImageResourceID.workflow_url


class AlphaIdentifiers(ImageResourceBlock):
    def __init__(self, name='', identifiers=[]):
        self.name = name
        self.identifiers = identifiers

    _resource_id = enums.ImageResourceID.alpha_identifiers

    @property
    def identifiers(self):
        "Alpha indentifiers"
        return self._identifiers

    @identifiers.setter
    def identifiers(self, value):
        util.assert_is_list_of(value, int, min=0, max=(1 << 32))
        self._identifiers = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        length = util.read_value(fd, 'I')
        buf = fd.read(4 * length)
        identifiers = list(np.frombuffer(buf, np.uint32))
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
    def __init__(self,
                 name='',
                 version=0,
                 has_real_merged_data=False,
                 writer='',
                 reader='',
                 file_version=0):
        self.name = name
        self.version = version
        self.has_real_merged_data = has_real_merged_data
        self.writer = writer
        self.reader = reader
        self.file_version = file_version

    _resource_id = enums.ImageResourceID.version_info

    @property
    def version(self):
        "version"
        return self._version

    @version.setter
    def version(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("version must be a 32-bit integer")
        self._version = value

    @property
    def has_real_merged_data(self):
        "has real merged data?"
        return self._has_real_merged_data

    @has_real_merged_data.setter
    def has_real_merged_data(self, value):
        self._has_real_merged_data = bool(value)

    @property
    def writer(self):
        "writer name"
        return self._writer

    @writer.setter
    def writer(self, value):
        if not isinstance(value, six.text_type):
            raise TypeError("writer must be a Unicode string")
        self._writer = value

    @property
    def reader(self):
        "reader name"
        return self._reader

    @reader.setter
    def reader(self, value):
        if not isinstance(value, six.text_type):
            raise TypeError("reader must be a Unicode string")
        self._reader = value

    @property
    def file_version(self):
        "file version"
        return self._file_version

    @file_version.setter
    def file_version(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("file_version must be a 32-bit integer")
        self._file_version = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        version, has_real_merged_data = util.read_value(fd, 'IB')
        has_real_merged_data = bool(has_real_merged_data)
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
        util.write_value(fd, 'IB', self.version, self.has_real_merged_data)
        util.write_unicode_string(fd, self.writer)
        util.write_unicode_string(fd, self.reader)
        util.write_value(fd, 'I', self.file_version)


class PrintScale(ImageResourceBlock):
    def __init__(self,
                 name='',
                 style=enums.PrintScaleStyle.centered,
                 x=0.0,
                 y=0.0,
                 scale=0.0):
        self.name = name
        self.style = style
        self.x = x
        self.y = y
        self.scale = scale

    _resource_id = enums.ImageResourceID.print_scale

    @property
    def style(self):
        "Style. See `enums.PrintScaleStyle`."
        return self._style

    @style.setter
    def style(self, value):
        if value not in list(enums.PrintScaleStyle):
            raise ValueError("Invalid print scale style")
        self._style = value

    @property
    def x(self):
        "x location"
        return self._x

    @x.setter
    def x(self, value):
        if not isinstance(value, float):
            raise TypeError("x must be a float")
        self._x = value

    @property
    def y(self):
        "y location"
        return self._y

    @y.setter
    def y(self, value):
        if not isinstance(value, float):
            raise TypeError("y must be a float")
        self._y = value

    @property
    def scale(self):
        "scale"
        return self._scale

    @scale.setter
    def scale(self, value):
        if not isinstance(value, float):
            raise TypeError("scale must be a float")
        self._scale = value

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        style, x, y, scale = util.read_value(fd, 'Hfff')
        return cls(
            name=name, style=style, x=x, y=y, scale=scale
        )

    def data_length(self, header):
        return (2 + 4 + 4 + 4)

    @util.trace_write
    def write_data(self, fd, header):
        util.write_value(fd, 'Hfff', self.style, self.x, self.y, self.scale)


class ImageResources(object):
    """
    The image resource block section.
    """
    def __init__(self, blocks=[]):
        self.blocks = blocks

    @property
    def blocks(self):
        "List of all `ImageResourceBlock` items."
        return self._blocks

    @blocks.setter
    def blocks(self, value):
        util.assert_is_list_of(value, ImageResourceBlock)
        self._blocks = value

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
