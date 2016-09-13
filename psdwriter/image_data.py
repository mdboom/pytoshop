# -*- coding: utf-8 -*-


import struct


import numpy as np
import traitlets as t


from . import decoding
from . import enums
from . import util


class ImageData(t.HasTraits):
    compression = t.Enum(
        list(enums.Compression),
        default_value=enums.Compression.raw)
    channels = t.Instance(np.ndarray, allow_none=True)

    @t.validate('channels')
    def _valid_channels(self, proposal):
        value = proposal['value']
        if value is None:
            return None
        if len(value.shape) != 3:
            raise ValueError("image must be a 3-dimensional array")
        if value.dtype.kind != 'u':
            raise ValueError("image must have unsigned integer data type")
        return value

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
        image = image.reshape(
            (header.num_channels, header.height, header.width))

        return cls(channels=image, compression=compression)

    def get_compressed(self, header):
        expected_shape = (header.num_channels, header.height, header.width)
        if self.channels is None:
            image = np.zeros(
                expected_shape,
                dtype=decoding.color_depth_dtype_map[header.depth])
        else:
            image = self.channels
            if image.shape != expected_shape:
                raise ValueError(
                    "Image data size does not match file size. "
                    "Got {}, expected {}".format(
                        image.shape, expected_shape))

        image = image.reshape(
            (header.height * header.num_channels, header.width))
        data = decoding.compress_image(
            image, self.compression, header.depth, header.version)
        return data

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'H', self.compression)
        data = self.get_compressed(header)
        fd.write(data)
