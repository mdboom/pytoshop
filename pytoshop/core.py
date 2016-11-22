# -*- coding: utf-8 -*-


"""
The core objects, including the `PsdFile` and its `Header`.
"""


from __future__ import unicode_literals, absolute_import


import struct


import traitlets as t


from . import color_mode
from . import docs
from . import enums
from . import image_data
from . import image_resources
from . import layers
from . import util


class Header(t.HasTraits):
    """
    Manages the header at the start of a PSD/PSB file.
    """

    version = t.Enum(
        list(enums.Version),
        default_value=enums.Version.version_1,
        help="The version of the file format. See `enums.Version`."
    )
    num_channels = t.Int(
        1, min=1, max=56,
        help="Number of color channels in the file."
    )
    height = t.Int(
        1, min=1, max=300000,
        help="Height of the image (in pixels)."
    )
    width = t.Int(
        1, min=1, max=300000,
        help="Width of the image (in pixels)."
    )
    depth = t.Enum(
        list(enums.ColorDepth),
        default_value=enums.ColorDepth.depth8,
        help="Number of bits per channel. See `enums.ColorDepth`."
    )
    color_mode = t.Enum(
        list(enums.ColorMode),
        default_value=enums.ColorMode.rgb,
        help="Color mode of the file. See `enums.ColorMode`."
    )

    max_size_mapping = {
        1: 30000,
        2: 300000
    }

    @t.observe('width', 'height')
    def _check_size(self, change):
        if change['new'] > self.max_size_mapping[self.version]:
            raise t.TraitError(
                '{} is too large for version {}. Must be <= {}'.format(
                    change['name'],
                    self.version,
                    self.max_size_mapping[self.version]))

    @property
    def shape(self):
        return (self.height, self.width)

    @classmethod
    @util.trace_read
    def header_read(cls, fd):
        data = fd.read(26)

        (signature, version, _reserved, num_channels,
         height, width, depth, color_mode) = struct.unpack('>4sH6sHIIHH', data)

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

    read = header_read

    @util.trace_write
    def write(self, fd):
        """
        Write to a file-like object.

        Parameters
        ----------
        fd : file-like object
            Must be writable, seekable and open in binary mode.
        """
        data = struct.pack(
            '>4sH6sHIIHH', b'8BPS', self.version, b'',
            self.num_channels, self.height, self.width, self.depth,
            self.color_mode)
        fd.write(data)
    write.__doc__ = docs.write_single


class PsdFile(Header):
    """
    Represents an entire PSD file.
    """

    color_mode_data = t.Instance(
        color_mode.ColorModeData,
        help='Color mode data section. See `color_mode.ColorModeData`.'
    )
    image_resources = t.Instance(
        image_resources.ImageResources,
        help='Image resources. See `image_resources.ImageResources`.'
    )
    layer_and_mask_info = t.Instance(
        layers.LayerAndMaskInfo,
        help='Layer and mask info. See `layers.LayerAndMaskInfo`.'
    )
    image_data = t.Instance(
        image_data.ImageData,
        help='Image data. See `image_data.ImageData`.'
    )

    @t.default('color_mode_data')
    def _default_color_mode_data(self):
        return color_mode.ColorModeData()

    @t.default('image_resources')
    def _default_image_resources(self):
        return image_resources.ImageResources()

    @t.default('layer_and_mask_info')
    def _default_layer_and_mask_info(self):
        return layers.LayerAndMaskInfo()

    @t.default('image_data')
    def _default_image_data(self):
        return image_data.ImageData()

    @classmethod
    @util.trace_read
    def read(cls, fd):
        self = cls.header_read(fd)
        self.color_mode_data = color_mode.ColorModeData.read(fd, self)
        self.image_resources = image_resources.ImageResources.read(fd, self)
        self.layer_and_mask_info = layers.LayerAndMaskInfo.read(fd, self)
        self.image_data = image_data.ImageData.read(fd, self)
        return self
    read.__func__.__doc__ = docs.read_single

    @util.trace_write
    def write(self, fd):
        Header.write(self, fd)
        self.color_mode_data.write(fd, self)
        self.image_resources.write(fd, self)
        self.layer_and_mask_info.write(fd, self)
        self.image_data.write(fd, self)
    write.__doc__ = docs.write_single
