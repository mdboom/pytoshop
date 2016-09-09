# -*- coding: utf-8 -*-


import traitlets as t


from . import color_mode
from . import enums
from . import image_data
from . import image_resources
from . import layers
from .util import BinaryStruct, trace_read, log, trace_write


class Header(t.HasTraits):
    structure = BinaryStruct(
        [('signature', '4s'),
         ('version', 'H'),
         ('_reserved', '6s'),
         ('num_channels', 'H'),
         ('height', 'I'),
         ('width', 'I'),
         ('depth', 'H'),
         ('color_mode', 'H')])

    signatures = {
        b'8BPS': 1,
        b'8BPB': 2
    }

    inverse_signatures = dict((v, k) for (k, v) in signatures.items())

    max_size_mapping = {
        1: 30000,
        2: 300000
    }

    @property
    def signature(self):
        return self.inverse_signatures[self.version]
    version = t.Enum(list(enums.Version))
    num_channels = t.Int(1, min=1, max=56)
    height = t.Int(1, min=1, max=300000)
    width = t.Int(1, min=1, max=300000)
    depth = t.Enum(list(enums.ColorDepth))
    color_mode = t.Enum(list(enums.ColorMode))

    @t.observe('width', 'height')
    def _check_size(self, change):
        if change['new'] > self.max_size_mapping[self.version]:
            raise t.TraitError(
                '{} is too large for version {}. Must be <= {}'.format(
                    change['name'],
                    self.version,
                    self.max_size_mapping[self.version]))

    @property
    def _reserved(self):
        return b'\0\0\0\0\0\0\0'

    @classmethod
    @trace_read
    def read(cls, fd):
        d = cls.structure.read(fd)

        if d['signature'] not in cls.signatures:
            raise ValueError("Invalid signature '{}'".format(d['signature']))
        if cls.signatures[d['signature']] != d['version']:
            raise ValueError("Signature and version mismatch")
        del d['signature']

        if d['_reserved'] != b'\0\0\0\0\0\0':
            raise ValueError("Reserved area unequal to zero")
        del d['_reserved']

        return cls(**d)

    @trace_write
    def write(self, fd):
        self.structure.write(fd, self)


class PsdFile(t.HasTraits):
    header = t.Instance(Header)
    color_mode_data = t.Instance(color_mode.ColorModeData)
    image_resources = t.Instance(image_resources.ImageResources)
    layers = t.Instance(layers.LayerAndMaskInfo)
    image_data = t.Instance(image_data.ImageData, allow_none=True)

    @classmethod
    @trace_read
    def read(cls, fd):
        header = Header.read(fd)
        color_mode_data = color_mode.ColorModeData.read(fd, header)
        resources = image_resources.ImageResources.read(fd, header)
        layer_info = layers.LayerAndMaskInfo.read(fd, header)
        data = image_data.ImageData.read(fd, header)

        return cls(
            header=header,
            color_mode_data=color_mode_data,
            image_resources=resources,
            layers=layer_info,
            image_data=data)

    @trace_write
    def write(self, fd):
        self.header.write(fd)
        self.color_mode_data.write(fd, self.header)
        self.image_resources.write(fd, self.header)
        self.layers.write(fd, self.header)
        if self.image_data is not None:
            self.image_data.write(fd, self.header)
