# -*- coding: utf-8 -*-


import struct


import numpy as np
import traitlets as t


from . import decoding
from . import enums
from . import util


class ImageData(t.HasTraits):
    compression = t.Enum(list(enums.Compression))
    image = t.Instance(np.ndarray)

    @t.validate
    def _valid_image(self, proposal):
        if len(proposal['value'].shape) not in (2, 3):
            raise ValueError("image must be 2- or 3-dimensional array")
        return proposal['value']

    def length(self, header):
        return len(self.get_compressed(header))

    def total_length(self, header):
        return 2 + self.length(header)

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        compression = fd.read(2)
        if compression == b'':
            raise IOError("Unexpected end of file")

        compression = struct.unpack('>H', compression)[0]
        util.log("compression: {}", enums.Compression(compression))

        data = fd.read()
        image = decoding.decompress_image(
            data, compression,
            (header.height * header.num_channels, header.width),
            header.depth, header.version)
        image = decoding.interlace_image(
            image, header.width, header.height, header.num_channels)

        return cls(image=image, compression=compression)

    def get_compressed(self, header):
        image = decoding.deinterlace_image(
            self.image, header.width, header.height, header.num_channels)
        data = decoding.compress_image(
            image, self.compression, header.depth, header.version)
        return data

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'H', self.compression)

        data = self.get_compressed(header)

        fd.write(data)
