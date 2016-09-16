# -*- coding: utf-8 -*-


"""
The `ImageData` section.
"""


import struct


import numpy as np
import traitlets as t


from . import codecs
from . import enums
from . import util


class ImageData(t.HasTraits):
    """
    Stores (non-layer) image data.
    """
    compression = t.Enum(
        list(enums.Compression),
        default_value=enums.Compression.raw,
        help="Compression method. See `enums.Compression`"
    )
    channels = t.Instance(
        np.ndarray,
        allow_none=True,
        help="The color channels in the image. "
        "A Numpy array of shape (num_channels, height, width). "
        "Must by unsigned integer and match the bit depth of the "
        "file as a whole."
    )

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
        image = codecs.decompress_image(
            data, compression,
            (header.height * header.num_channels, header.width),
            header.depth, header.version)
        image = image.reshape(
            (header.num_channels, header.height, header.width))

        return cls(channels=image, compression=compression)

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'H', self.compression)

        expected_shape = (header.num_channels, header.height, header.width)
        if self.channels is None:
            image = np.zeros(
                expected_shape,
                dtype=codecs.color_depth_dtype_map[header.depth])
        else:
            image = self.channels
            if image.shape != expected_shape:
                raise ValueError(
                    "Image data size does not match file size. "
                    "Got {}, expected {}".format(
                        image.shape, expected_shape))

        image = image.reshape(
            (header.height * header.num_channels, header.width))
        codecs.compress_image(
            fd, image, self.compression, header.depth, header.version)
