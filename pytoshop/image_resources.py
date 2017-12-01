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


from typing import Any, BinaryIO, Dict, List, Optional, Type, TYPE_CHECKING, Union  # NOQA
if TYPE_CHECKING:
    from . import core  # NOQA


class _ImageResourceBlockMeta(type):
    """
    A metaclass that builds a mapping of subclasses.
    """
    mapping = {}  # type: Dict[int, Type[ImageResourceBlock]]

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
    _resource_id = -1

    @property
    def name(self):  # type: (...) -> unicode
        "Name of image resource."
        return self._name

    @name.setter
    def name(self, value):  # type: (Union[bytes, unicode]) -> None
        if isinstance(value, bytes):
            value = value.decode('ascii')

        if (not isinstance(value, six.text_type) or
                len(value) > 255):
            raise ValueError("name must be unicode string of length < 255")
        self._name = value

    @property
    def resource_id(self):  # type: (...) -> int
        "Type of image resource."
        return self._resource_id

    def length(self, header):  # type: (core.Header) -> int
        data_length = self.data_length(header)
        length = (
            4 + 2 +
            util.pascal_string_length(self.name, 2) +
            4 + data_length
        )
        if data_length % 2 != 0:
            length += 1
        return length
    length.__doc__ = docs.length  # type: ignore

    def total_length(self, header):  # type: (core.Header) -> int
        return self.length(header)
    total_length.__doc__ = docs.total_length  # type: ignore

    def data_length(self, header):  # type: (core.Header) -> int
        raise NotImplementedError()

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        # type: (BinaryIO, core.Header) -> ImageResourceBlock
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
    read.__func__.__doc__ = docs.read  # type: ignore

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  data_length,  # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        raise NotImplementedError()

    @util.trace_write
    def write(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
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
    write.__doc__ = docs.write  # test: ignore

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        raise NotImplementedError()


class GenericImageResourceBlock(ImageResourceBlock):
    def __init__(self, name='', resource_id=0, data=b''):
        self.name = name
        self.resource_id = resource_id
        self.data = data

    @property
    def resource_id(self):  # type: (...) -> int
        "Type of image resource."
        return self._resource_id

    @resource_id.setter
    def resource_id(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 16)):
            raise ValueError(
                "resource_id must be a 16-bit positive integer"
            )
        self._resource_id = value

    @property
    def data(self):  # type: (...) -> bytes
        "Raw data of image resource."
        return self._data

    @data.setter
    def data(self, value):  # type: (bytes) -> None
        if (not isinstance(value, bytes) or
                len(value) > (1 << 32)):
            raise ValueError("data must be a byte string")
        self._data = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        data = fd.read(length)
        return cls(resource_id=resource_id, name=name, data=data)

    def data_length(self, header):  # type: (core.Header) -> int
        return len(self.data)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        fd.write(self.data)


class ImageResourceUnicodeString(ImageResourceBlock):
    def __init__(self,
                 name='',  # type: unicode
                 value=''  # type: unicode
                 ):  # type: (...) -> None
        self.name = name
        self.value = value

    @property
    def value(self):  # type: (...) -> unicode
        return self._value

    @value.setter
    def value(self, value):  # type: (unicode) -> None
        if (not isinstance(value, six.text_type) or
                len(value) > (1 << 32)):
            raise TypeError("value must be a unicode string")
        self._value = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        data = fd.read(length)
        value = util.decode_unicode_string(data)
        return cls(
            name=name, value=value
        )

    def data_length(self, header):  # type: (core.Header) -> int
        return util.unicode_string_length(self.value)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        fd.write(util.encode_unicode_string(self.value))


class LayersGroupInfo(ImageResourceBlock):
    """
    Layers group information.

    Indicates which layers are locked together.
    """
    def __init__(self,
                 name='',      # type: unicode
                 group_ids=[]  # type: List[int]
                 ):  # type: (...) -> None
        self.name = name
        self.group_ids = group_ids

    _resource_id = enums.ImageResourceID.layers_group_info

    @property
    def group_ids(self):  # type: (...) -> List[int]
        return self._group_ids

    @group_ids.setter
    def group_ids(self, value):  # type: (List[int]) -> None
        util.assert_is_list_of(value, int, min=0, max=65535)
        self._group_ids = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        data = fd.read(length)
        group_ids = np.frombuffer(data, '>u2').tolist()
        return cls(name=name, group_ids=group_ids)

    def data_length(self, header):  # type: (core.Header) -> int
        return len(self.group_ids * 2)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        data = np.array(self.group_ids, '>u2').tobytes()
        fd.write(data)


class BorderInfo(ImageResourceBlock):
    """
    Border information.
    """
    def __init__(self,
                 name='',                 # type: unicode
                 border_width_num=0,      # type: int
                 border_width_den=1,      # type: int
                 unit=enums.Units.inches  # type: int
                 ):  # type: (...) -> None
        self.name = name
        self.border_width_num = border_width_num
        self.border_width_den = border_width_den
        self.unit = unit

    _resource_id = enums.ImageResourceID.border_info

    @property
    def border_width_num(self):  # type: (...) -> int
        "Border width numerator"
        return self._border_width_num

    @border_width_num.setter
    def border_width_num(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < 0 or value > 65535):
            raise ValueError(
                "border_width_num must be integer in range 0-65535"
            )
        self._border_width_num = value

    @property
    def border_width_den(self):  # type: (...) -> int
        "Border width denominator"
        return self._border_width_den

    @border_width_den.setter
    def border_width_den(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < 1 or value > 65535):
            raise ValueError(
                "border_width_den must be integer in range 1-65535"
            )
        self._border_width_den = value

    @property
    def unit(self):  # type: (...) -> int
        "Unit. See `enums.Units`."
        return self._unit

    @unit.setter
    def unit(self, value):  # type: (int) -> None
        if value not in list(enums.Units):  # type: ignore
            raise ValueError("Invalid unit.")
        self._unit = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        num, den, unit = util.read_value(fd, 'HHH')
        return cls(
            name=name, border_width_num=num, border_width_den=den,
            unit=unit)

    def data_length(self, header):  # type: (core.Header) -> int
        return 6

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(
            fd, 'HHH', self.border_width_num,
            self.border_width_den, self.unit
        )


class BackgroundColor(ImageResourceBlock):
    """
    Background color.
    """
    def __init__(self,
                 name='',                           # type: unicode
                 color_space=enums.ColorSpace.rgb,  # type: int
                 color=[]                           # type: List[int]
                 ):  # type: (...) -> None
        self.name = name
        self.color_space = color_space
        self.color = color

    _resource_id = enums.ImageResourceID.background_color

    @property
    def color_space(self):  # type: (...) -> int
        "The color space. See `enums.ColorSpace`"
        return self._color_space

    @color_space.setter
    def color_space(self, value):  # type: (int) -> None
        if value not in list(enums.ColorSpace):  # type: ignore
            raise ValueError("Invalid color space.")
        self._color_space = value

    @property
    def color(self):  # type: (...) -> List[int]
        """
        The color data.  If the color data does not require 4 values,
        the extra values are undefined and should be included as
        zeros.
        """
        return self._color

    @color.setter
    def color(self, value):  # type: (List[int]) -> None
        util.assert_is_list_of(value, int, -32767, 65536)
        if len(value) < 1 or len(value) > 4:
            raise ValueError("Color must be of length 1-4")
        self._color = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        space_id, a, b, c, d = util.read_value(fd, 'HHHHH')
        if space_id == enums.ColorSpace.lab:
            b -= 32767
            c -= 32767
        return cls(
            name=name, color_space=space_id, color=[a, b, c, d]
        )

    def data_length(self, header):  # type: (core.Header) -> int
        return 10

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
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
                 name='',                   # type: unicode
                 labels=False,              # type: bool
                 crop_marks=False,          # type: bool
                 color_bars=False,          # type: bool
                 registration_marks=False,  # type: bool
                 negative=False,            # type: bool
                 flip=False,                # type: bool
                 interpolate=False,         # type: bool
                 caption=False,             # type: bool
                 print_flags=False          # type: bool
                 ):  # type: (...) -> None
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
    def labels(self):  # type: (...) -> bool
        "labels"
        return self._labels

    @labels.setter
    def labels(self, value):  # type: (Any) -> None
        self._labels = bool(value)

    @property
    def crop_marks(self):  # type: (...) -> bool
        "crop marks"
        return self._crop_marks

    @crop_marks.setter
    def crop_marks(self, value):  # type: (Any) -> None
        self._crop_marks = bool(value)

    @property
    def color_bars(self):  # type: (...) -> bool
        "color bars"
        return self._color_bars

    @color_bars.setter
    def color_bars(self, value):  # type: (Any) -> None
        self._color_bars = bool(value)

    @property
    def registration_marks(self):  # type: (...) -> bool
        "registration marks"
        return self._registration_marks

    @registration_marks.setter
    def registration_marks(self, value):  # type: (Any) -> None
        self._registration_marks = bool(value)

    @property
    def negative(self):  # type: (...) -> bool
        "negative"
        return self._negative

    @negative.setter
    def negative(self, value):  # type: (Any) -> None
        self._negative = bool(value)

    @property
    def flip(self):  # type: (...) -> bool
        "flip"
        return self._flip

    @flip.setter
    def flip(self, value):  # type: (Any) -> None
        self._flip = bool(value)

    @property
    def interpolate(self):  # type: (...) -> bool
        "interpolate"
        return self._interpolate

    @interpolate.setter
    def interpolate(self, value):  # type: (Any) -> None
        self._interpolate = bool(value)

    @property
    def caption(self):  # type: (...) -> bool
        "caption"
        return self._caption

    @caption.setter
    def caption(self, value):  # type: (Any) -> None
        self._caption = bool(value)

    @property
    def print_flags(self):  # type: (...) -> bool
        "print flags"
        return self._print_flags

    @print_flags.setter
    def print_flags(self, value):  # type: (Any) -> None
        self._print_flags = bool(value)

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        vals = util.read_value(fd, 'BBBBBBBBB')
        vals = [bool(x) for x in vals]
        return cls(
            name=name, labels=vals[0], crop_marks=vals[1],
            color_bars=vals[2], registration_marks=vals[3],
            negative=vals[4], flip=vals[5], interpolate=vals[6],
            caption=vals[7], print_flags=vals[8]
        )

    def data_length(self, header):  # type: (core.Header) -> int
        return 9

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        vals = [
            self.labels, self.crop_marks, self.color_bars,
            self.registration_marks, self.negative, self.flip,
            self.interpolate, self.caption, self.print_flags
        ]
        int_vals = [(x and 255 or 0) for x in vals]
        util.write_value(fd, 'BBBBBBBBB', *int_vals)


class GuideResourceBlock(object):
    def __init__(self,
                 location=0,  # type: int
                 direction=enums.GuideDirection.vertical  # type: int
                 ):  # type: (...) -> None
        self.location = location
        self.direction = direction

    @property
    def location(self):  # type: (...) -> int
        "Location of guide in document coordinates."
        return self._location

    @location.setter
    def location(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("location must be a 32-bit unsigned int")
        self._location = value

    @property
    def direction(self):  # type: (...) -> int
        "Guide direction. See `enums.GuideDirection`."
        return self._direction

    @direction.setter
    def direction(self, value):  # type: (int) -> None
        if value not in list(enums.GuideDirection):  # type: ignore
            raise ValueError("Invalid guide direction")
        self._direction = value

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        # type: (BinaryIO, core.Header) -> GuideResourceBlock
        location, direction = util.read_value(fd, 'IB')
        return cls(location=location, direction=direction)

    @util.trace_write
    def write(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'IB', self.location, self.direction)

    def data_length(self, header):  # type: (core.Header) -> int
        return 5


class GridAndGuidesInfo(ImageResourceBlock):
    """
    Grid and guides resource.
    """
    def __init__(self,
                 name='',      # type: unicode
                 grid_hori=0,  # type: int
                 grid_vert=0,  # type: int
                 guides=[]     # type: List[GuideResourceBlock]
                 ):  # type: (...) -> None
        self.name = name
        self.grid_hori = grid_hori
        self.grid_vert = grid_vert
        self.guides = guides

    _resource_id = enums.ImageResourceID.grid_and_guides_info

    @property
    def version(self):  # type: (...) -> int
        return 1

    @property
    def grid_hori(self):  # type: (...) -> int
        "Document-specific grid (horizontal). In 1/32 pt."
        return self._grid_hori

    @grid_hori.setter
    def grid_hori(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("grid_hori must be a 32-bit unsigned int")
        self._grid_hori = value

    @property
    def grid_vert(self):  # type: (...) -> int
        "Document-specific grid (vertical). In 1/32 pt."
        return self._grid_vert

    @grid_vert.setter
    def grid_vert(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("grid_vert must be a 32-bit unsigned int")
        self._grid_vert = value

    @property
    def guides(self):  # type: (...) -> List[GuideResourceBlock]
        "Guides.  See `GuideResourceBlock`."
        return self._guides

    @guides.setter
    def guides(self, value):  # type: (List[GuideResourceBlock]) -> None
        util.assert_is_list_of(value, GuideResourceBlock)
        self._guides = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
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

    def data_length(self, header):  # type: (core.Header) -> int
        return 16 + (5 * len(self.guides))

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(
            fd, 'IIII', self.version,
            self.grid_hori, self.grid_vert,
            len(self.guides)
        )
        for guide in self.guides:
            guide.write(fd, header)


class CopyrightFlag(ImageResourceBlock):
    def __init__(self,
                 name='',         # type: unicode
                 copyright=False  # type: bool
                 ):  # type: (...) -> None
        self.name = name
        self.copyright = copyright

    _resource_id = enums.ImageResourceID.copyright_flag

    @property
    def copyright(self):  # type: (...) -> bool
        "Is copyrighted?"
        return self._copyright

    @copyright.setter
    def copyright(self, value):  # type: (Any) -> None
        self._copyright = bool(value)

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        copyright = bool(util.read_value(fd, 'B'))
        return cls(
            name=name, copyright=copyright
        )

    def data_length(self, header):  # type: (core.Header) -> int
        return 1

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'B', self.copyright and 255 or 0)


class Url(ImageResourceBlock):
    def __init__(self,
                 name='',  # type: unicode
                 url=b''   # type: bytes
                 ):  # type: (...) -> None
        self.name = name
        self.url = url

    _resource_id = enums.ImageResourceID.url

    @property
    def url(self):  # type: (...) -> bytes
        "URL"
        return self._url

    @url.setter
    def url(self, value):  # type: (bytes) -> None
        if not isinstance(value, bytes):
            raise TypeError("url must be bytes string")
        self._url = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        url = fd.read(length)
        return cls(
            name=name, url=url
        )

    def data_length(self, header):  # type: (core.Header) -> int
        return len(self.url)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        fd.write(self.url)


class GlobalAngle(ImageResourceBlock):
    def __init__(self,
                 name='',  # type: unicode
                 angle=0   # type: int
                 ):  # type: (...) -> None
        self.name = name
        self.angle = angle

    _resource_id = enums.ImageResourceID.global_angle

    @property
    def angle(self):  # type: (...) -> int
        "Global light angle for the effect layer"
        return self._angle

    @angle.setter
    def angle(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < -360 or value > 360):
            raise ValueError(
                "angle must be an int in range -360 to 360"
            )
        self._angle = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        angle = util.read_value(fd, 'i')
        return cls(
            name=name, angle=angle
        )

    def data_length(self, header):  # type: (core.Header) -> int
        return 4

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'i', self.angle)


class EffectsVisible(ImageResourceBlock):
    def __init__(self,
                 name='',       # type: unicode
                 visible=False  # type: bool
                 ):  # type: (...) -> None
        self.name = name
        self.visible = visible

    _resource_id = enums.ImageResourceID.effects_visible

    @property
    def visible(self):  # type: (...) -> bool
        "Are effects visible?"
        return self._visible

    @visible.setter
    def visible(self, value):  # type: (Any) -> None
        self._visible = bool(value)

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        visible = bool(util.read_value(fd, 'B'))
        return cls(
            name=name, visible=visible
        )

    def data_length(self, header):  # type: (core.Header) -> int
        return 1

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'B', self.visible and 255 or 0)


class DocumentSpecificIdsSeedNumber(ImageResourceBlock):
    def __init__(self,
                 name='',      # type: unicode
                 base_value=0  # type: int
                 ):  # type: (...) -> None
        self.name = name
        self.base_value = base_value

    _resource_id = enums.ImageResourceID.document_specific_ids_seed_number

    @property
    def base_value(self):  # type: (...) -> int
        "Base value"
        return self._base_value

    @base_value.setter
    def base_value(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("base_value must be a 32-bit integer")
        self._base_value = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        base_value = bool(util.read_value(fd, 'I'))
        return cls(
            name=name, base_value=base_value
        )

    def data_length(self, header):  # type: (core.Header) -> int
        return 4

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'I', self.base_value)


class UnicodeAlphaNames(ImageResourceUnicodeString):
    _resource_id = enums.ImageResourceID.unicode_alpha_names


class GlobalAltitude(ImageResourceBlock):
    def __init__(self,
                 name='',    # type: unicode
                 altitude=0  # type: int
                 ):  # type: (...) -> None
        self.name = name
        self.altitude = altitude

    _resource_id = enums.ImageResourceID.global_altitude

    @property
    def altitude(self):  # type: (...) -> int
        "Global altitude"
        return self._altitude

    @altitude.setter
    def altitude(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("altitude must be a 32-bit integer")
        self._altitude = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        altitude = util.read_value(fd, 'I')
        return cls(
            name=name, altitude=altitude
        )

    def data_length(self, header):  # type: (core.Header) -> int
        return 4

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'I', self.altitude)


class WorkflowUrl(ImageResourceUnicodeString):
    _resource_id = enums.ImageResourceID.workflow_url


class AlphaIdentifiers(ImageResourceBlock):
    def __init__(self,
                 name='',        # type: unicode
                 identifiers=[]  # type: List[int]
                 ):  # type: (...) -> None
        self.name = name
        self.identifiers = identifiers

    _resource_id = enums.ImageResourceID.alpha_identifiers

    @property
    def identifiers(self):  # type: (...) -> List[int]
        "Alpha indentifiers"
        return self._identifiers

    @identifiers.setter
    def identifiers(self, value):  # type: (List[int]) -> None
        util.assert_is_list_of(value, int, min=0, max=(1 << 32))
        self._identifiers = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        length = util.read_value(fd, 'I')
        buf = fd.read(4 * length)
        identifiers = list(np.frombuffer(buf, np.uint32))
        return cls(
            name=name, identifiers=identifiers
        )

    def data_length(self, header):  # type: (core.Header) -> int
        return 4 + (len(self.identifiers) * 4)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'I', len(self.identifiers))
        for identifier in self.identifiers:
            util.write_value(fd, 'I', identifier)


class VersionInfo(ImageResourceBlock):
    def __init__(self,
                 name='',                     # type: unicode
                 version=0,                   # type: int
                 has_real_merged_data=False,  # type: bool
                 writer='',                   # type: unicode
                 reader='',                   # type: unicode
                 file_version=0               # type: int
                 ):  # type: (...) -> None
        self.name = name
        self.version = version
        self.has_real_merged_data = has_real_merged_data
        self.writer = writer
        self.reader = reader
        self.file_version = file_version

    _resource_id = enums.ImageResourceID.version_info

    @property
    def version(self):  # type: (...) -> int
        "version"
        return self._version

    @version.setter
    def version(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("version must be a 32-bit integer")
        self._version = value

    @property
    def has_real_merged_data(self):  # type: (...) -> bool
        "has real merged data?"
        return self._has_real_merged_data

    @has_real_merged_data.setter
    def has_real_merged_data(self, value):  # type: (Any) -> None
        self._has_real_merged_data = bool(value)

    @property
    def writer(self):  # type: (...) -> unicode
        "writer name"
        return self._writer

    @writer.setter
    def writer(self, value):  # type: (unicode) -> None
        if not isinstance(value, six.text_type):
            raise TypeError("writer must be a Unicode string")
        self._writer = value

    @property
    def reader(self):  # type: (...) -> unicode
        "reader name"
        return self._reader

    @reader.setter
    def reader(self, value):  # type: (unicode) -> None
        if not isinstance(value, six.text_type):
            raise TypeError("reader must be a Unicode string")
        self._reader = value

    @property
    def file_version(self):  # type: (...) -> int
        "file version"
        return self._file_version

    @file_version.setter
    def file_version(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < 0 or value > (1 << 32)):
            raise ValueError("file_version must be a 32-bit integer")
        self._file_version = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
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

    def data_length(self, header):  # type: (core.Header) -> int
        return (
            4 + 1 +
            util.unicode_string_length(self.writer) +
            util.unicode_string_length(self.reader) +
            4)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'IB', self.version, self.has_real_merged_data)
        util.write_unicode_string(fd, self.writer)
        util.write_unicode_string(fd, self.reader)
        util.write_value(fd, 'I', self.file_version)


class PrintScale(ImageResourceBlock):
    def __init__(self,
                 name='',                               # type: unicode
                 style=enums.PrintScaleStyle.centered,  # type: int
                 x=0.0,                                 # type: float
                 y=0.0,                                 # type: float
                 scale=0.0                              # type: float
                 ):  # type: (...) -> None
        self.name = name
        self.style = style
        self.x = x
        self.y = y
        self.scale = scale

    _resource_id = enums.ImageResourceID.print_scale

    @property
    def style(self):  # type: (...) -> int
        "Style. See `enums.PrintScaleStyle`."
        return self._style

    @style.setter
    def style(self, value):  # type: (int) -> None
        if value not in list(enums.PrintScaleStyle):  # type: ignore
            raise ValueError("Invalid print scale style")
        self._style = value

    @property
    def x(self):  # type: (...) -> float
        "x location"
        return self._x

    @x.setter
    def x(self, value):  # type: (float) -> None
        if not isinstance(value, float):
            raise TypeError("x must be a float")
        self._x = value

    @property
    def y(self):  # type: (...) -> float
        "y location"
        return self._y

    @y.setter
    def y(self, value):  # type: (float) -> None
        if not isinstance(value, float):
            raise TypeError("y must be a float")
        self._y = value

    @property
    def scale(self):  # type: (...) -> float
        "scale"
        return self._scale

    @scale.setter
    def scale(self, value):  # type: (float) -> None
        if not isinstance(value, float):
            raise TypeError("scale must be a float")
        self._scale = value

    @classmethod
    def read_data(cls,
                  fd,           # type: BinaryIO
                  resource_id,  # type: int
                  name,         # type: unicode
                  length,       # type: int
                  header        # type: core.Header
                  ):            # type: (...) -> ImageResourceBlock
        style, x, y, scale = util.read_value(fd, 'Hfff')
        return cls(
            name=name, style=style, x=x, y=y, scale=scale
        )

    def data_length(self, header):  # type: (core.Header) -> int
        return (2 + 4 + 4 + 4)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'Hfff', self.style, self.x, self.y, self.scale)


class ImageResources(object):
    """
    The image resource block section.
    """
    def __init__(self,
                 blocks=[]  # type: List[ImageResourceBlock]
                 ):  # type: (...) -> None
        self.blocks = blocks

    @property
    def blocks(self):  # type: (...) -> List[ImageResourceBlock]
        "List of all `ImageResourceBlock` items."
        return self._blocks

    @blocks.setter
    def blocks(self, value):  # type: (List[ImageResourceBlock]) -> None
        util.assert_is_list_of(value, ImageResourceBlock)
        self._blocks = value

    def length(self, header):  # type: (core.Header) -> int
        return sum(block.total_length(header) for block in self.blocks)
    length.__doc__ = docs.length  # type: ignore

    def total_length(self, header):  # type: (core.Header) -> int
        return 4 + self.length(header)
    total_length.__doc__ = docs.total_length  # type: ignore

    def get_block(self, resource_id):
        # type: (int) -> Optional[ImageResourceBlock]
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
        # type: (BinaryIO, core.Header) -> ImageResources
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
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'I', self.length(header))
        for block in self.blocks:
            block.write(fd, header)
    write.__doc__ = docs.write
