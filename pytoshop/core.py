# -*- coding: utf-8 -*-


"""
The core objects, including the `PsdFile` and its `Header`.
"""


from __future__ import unicode_literals, absolute_import


from typing import BinaryIO, Dict, Optional, Tuple  # NOQA


from .color_mode import ColorModeData
from . import docs
from . import enums
from .image_data import ImageData
from .image_resources import ImageResources
from .layers import LayerAndMaskInfo
from . import util


class Header(object):
    """
    Manages the header at the start of a PSD/PSB file.
    """
    def __init__(self,
                 version=enums.Version.version_1,  # type: int
                 num_channels=1,                   # type: int
                 height=1,                         # type: int
                 width=1,                          # type: int
                 depth=enums.ColorDepth.depth8,    # type: int
                 color_mode=enums.ColorMode.rgb    # type: int
                 ):  # type: (...) -> None
        self.version = version
        self.num_channels = num_channels
        self.height = height
        self.width = width
        self.depth = depth
        self.color_mode = color_mode

    @property
    def version(self):  # type: (...) -> int
        "The version of the file format. See `enums.Version`."
        return self._version

    @version.setter
    def version(self, value):  # type: (int) -> None
        if value not in list(enums.Version):  # type: ignore
            raise ValueError("Invalid version.")
        self._version = value

    @property
    def num_channels(self):  # type: (...) -> int
        "Number of color channels in the file."
        return self._num_channels

    @num_channels.setter
    def num_channels(self, value):  # type: (int) -> None
        if not isinstance(value, int):
            raise TypeError("num_channels must be an integer")
        if value < 1 or value > 56:
            raise TypeError("num_channels must be in range 1-56")
        self._num_channels = value

    @property
    def height(self):  # type: (...) -> int
        "Height of the image (in pixels)."
        return self._height

    @height.setter
    def height(self, value):  # type: (int) -> None
        if not isinstance(value, int):
            raise TypeError("height must be an integer")
        version_max = self.max_size_mapping[self.version]
        if value < 1 or value > version_max:
            raise ValueError(
                "height must be in range 1-{}".format(version_max)
            )
        self._height = value

    @property
    def width(self):  # type: (...) -> int
        "Width of the image (in pixels)."
        return self._width

    @width.setter
    def width(self, value):  # type: (int) -> None
        if not isinstance(value, int):
            raise TypeError("width must be an integer")
        version_max = self.max_size_mapping[self.version]
        if value < 1 or value > version_max:
            raise ValueError(
                "width must be in range 1-{}".format(version_max)
            )
        self._width = value

    @property
    def depth(self):  # type: (...) -> int
        "Number of bits per channel. See `enums.ColorDepth`."
        return self._depth

    @depth.setter
    def depth(self, value):  # type: (int) -> None
        if value not in list(enums.ColorDepth):  # type: ignore
            raise ValueError("Invalid depth")
        self._depth = value

    @property
    def color_mode(self):  # type: (...) -> int
        "Color mode of the file. See `enums.ColorMode`."
        return self._color_mode

    @color_mode.setter
    def color_mode(self, value):  # type: (int) -> None
        if value not in list(enums.ColorMode):  # type: ignore
            raise ValueError("Invalid color mode.")
        self._color_mode = value

    max_size_mapping = {
        1: 30000,
        2: 300000
    }  # type: Dict[int, int]

    @property
    def shape(self):  # type: (...) -> Tuple[int, int]
        return (self.height, self.width)

    @classmethod
    @util.trace_read
    def header_read(cls, fd):  # type: (BinaryIO) -> Header
        (signature, version, _reserved, num_channels,
         height, width, depth, color_mode) = util.read_value(fd, '4sH6sHIIHH')

        if signature != b'8BPS':
            raise ValueError("Invalid signature '{}'".format(signature))

        util.log(
            'version: {}, num_channels: {}, '
            'width: {}, height: {}, depth: {}, '
            'color_mode: {}',
            enums.Version(version), num_channels, width, height,
            depth, enums.ColorMode(color_mode)
        )

        return cls(version=version, num_channels=num_channels,
                   width=width, height=height, depth=depth,
                   color_mode=color_mode)
    header_read.__func__.__doc__ = docs.read_single

    @util.trace_write
    def write(self, fd):  # type: (BinaryIO) -> None
        """
        Write to a file-like object.

        Parameters
        ----------
        fd : file-like object
            Must be writable, seekable and open in binary mode.
        """
        util.write_value(
            fd, '4sH6sHIIHH', b'8BPS', self.version, b'',
            self.num_channels, self.height, self.width, self.depth,
            self.color_mode
        )
    write.__doc__ = docs.write_single


class PsdFile(Header):
    """
    Represents an entire PSD file.
    """
    def __init__(
            self,
            version=enums.Version.version_1,  # type: int
            num_channels=1,                   # type: int
            height=1,                         # type: int
            width=1,                          # type: int
            depth=enums.ColorDepth.depth8,    # type: int
            color_mode=enums.ColorMode.rgb,   # type: int
            color_mode_data=None,  # type: Optional[ColorModeData]
            image_resources=None,  # type: Optional[ImageResources]
            layer_and_mask_info=None,  # type: Optional[LayerAndMaskInfo]
            image_data=None,  # type: Optional[ImageData]
            compression=enums.Compression.raw  # type: int
            ):  # type: (...) -> None
        Header.__init__(
            self,
            version=version,
            num_channels=num_channels,
            height=height,
            width=width,
            depth=depth,
            color_mode=color_mode
        )

        if color_mode_data is None:
            color_mode_data = ColorModeData()
        self.color_mode_data = color_mode_data
        if image_resources is None:
            image_resources = ImageResources()
        self.image_resources = image_resources
        if layer_and_mask_info is None:
            layer_and_mask_info = LayerAndMaskInfo()
        self.layer_and_mask_info = layer_and_mask_info
        if image_data is None:
            image_data = ImageData(compression=compression)
        self.image_data = image_data

    @property
    def color_mode_data(self):
        # type: (...) -> ColorModeData
        'Color mode data section. See `color_mode.ColorModeData`.'
        return self._color_mode_data

    @color_mode_data.setter
    def color_mode_data(self, value):
        # type: (ColorModeData) -> None
        if not isinstance(value, ColorModeData):
            raise TypeError("color_mode_data must be ColorModeData instance")
        self._color_mode_data = value

    @property
    def image_resources(self):
        # type: (...) -> ImageResources
        'Image resources. See `image_resources.ImageResources`.'
        return self._image_resources

    @image_resources.setter
    def image_resources(self, value):
        # type: (ImageResources) -> None
        if not isinstance(value, ImageResources):
            raise TypeError("image_resources must be ImageResources instance")
        self._image_resources = value

    @property
    def layer_and_mask_info(self):
        # type: (...) -> LayerAndMaskInfo
        'Image resources. See `image_resources.ImageResources`.'
        return self._layer_and_mask_info

    @layer_and_mask_info.setter
    def layer_and_mask_info(self, value):
        # type: (LayerAndMaskInfo) -> None
        if not isinstance(value, LayerAndMaskInfo):
            raise TypeError(
                "layer_and_mask_info must be LayerAndMaskInfo instance"
            )
        self._layer_and_mask_info = value

    @property
    def image_data(self):
        # type: (...) -> ImageData
        'Image data. See `image_data.ImageData`.'
        return self._image_data

    @image_data.setter
    def image_data(self, value):
        # type: (ImageData) -> None
        if not isinstance(value, ImageData):
            raise TypeError("image_data must be ImageData instance")
        self._image_data = value

    @classmethod
    @util.trace_read
    def read(cls, fd):  # type: (BinaryIO) -> PsdFile
        self = cls.header_read(fd)
        self.color_mode_data = ColorModeData.read(fd, self)
        self.image_resources = ImageResources.read(fd, self)
        self.layer_and_mask_info = LayerAndMaskInfo.read(fd, self)
        self.image_data = ImageData.read(fd, self)
        return self
    read.__func__.__doc__ = docs.read_single

    @util.trace_write
    def write(self, fd):  # type: ignore
        Header.write(self, fd)
        self.color_mode_data.write(fd, self)
        self.image_resources.write(fd, self)
        self.layer_and_mask_info.write(fd, self)
        self.image_data.write(fd, self)
    write.__doc__ = docs.write_single
