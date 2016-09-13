# -*- coding: utf-8 -*-


import struct


import traitlets as t


from . import color_mode
from . import enums
from . import image_data
from . import image_resources
from . import layers
from . import util


class Header(t.HasTraits):
    version = t.Enum(
        list(enums.Version),
        default_value=enums.Version.version_1)
    num_channels = t.Int(1, min=1, max=56)
    height = t.Int(1, min=1, max=300000)
    width = t.Int(1, min=1, max=300000)
    depth = t.Enum(
        list(enums.ColorDepth),
        default_value=enums.ColorDepth.depth8)
    color_mode = t.Enum(
        list(enums.ColorMode),
        default_value=enums.ColorMode.rgb)

    signatures = {
        b'8BPS': 1,
        b'8BPB': 2
    }

    inverse_signatures = dict((v, k) for (k, v) in signatures.items())

    @property
    def signature(self):
        return self.inverse_signatures[self.version]

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

    @classmethod
    @util.trace_read
    def read(cls, fd):
        data = fd.read(26)

        (signature, version, _reserved, num_channels,
         height, width, depth, color_mode) = struct.unpack('>4sH6sHIIHH', data)

        if signature not in cls.signatures:
            raise ValueError("Invalid signature '{}'".format(signature))
        if cls.signatures[signature] != version:
            raise ValueError("Signature and version mismatch")

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

    @util.trace_write
    def write(self, fd):
        data = struct.pack(
            '>4sH6sHIIHH', self.signature, self.version, b'',
            self.num_channels, self.height, self.width, self.depth,
            self.color_mode)
        fd.write(data)


class PsdFile(t.HasTraits):
    header = t.Instance(Header)
    color_mode_data = t.Instance(color_mode.ColorModeData)
    image_resources = t.Instance(image_resources.ImageResources)
    layer_and_mask_info = t.Instance(layers.LayerAndMaskInfo)
    image_data = t.Instance(image_data.ImageData)

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
        header = Header.read(fd)
        color_mode_data = color_mode.ColorModeData.read(fd, header)
        resources = image_resources.ImageResources.read(fd, header)
        layer_and_mask_info = layers.LayerAndMaskInfo.read(fd, header)
        data = image_data.ImageData.read(fd, header)

        return cls(
            header=header,
            color_mode_data=color_mode_data,
            image_resources=resources,
            layer_and_mask_info=layer_and_mask_info,
            image_data=data)

    @util.trace_write
    def write(self, fd):
        self.header.write(fd)
        self.color_mode_data.write(fd, self.header)
        self.image_resources.write(fd, self.header)
        self.layer_and_mask_info.write(fd, self.header)
        self.image_data.write(fd, self.header)
