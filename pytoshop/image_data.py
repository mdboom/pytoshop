# -*- coding: utf-8 -*-


"""
The `ImageData` section.
"""


from __future__ import unicode_literals, absolute_import


import struct


from . import codecs
from . import enums
from . import util


class ImageData(object):
    """
    Stores (non-layer) image data.
    """
    def __init__(self, channels=None, fd=None, offset=None, size=None,
                 height=None, width=None, num_channels=None, depth=None,
                 version=None, compression=enums.Compression.raw):
        self.compression = compression
        if channels is not None:
            if (fd is not None or offset is not None or size is not None or
                    height is not None or width is not None or
                    num_channels is not None or depth is not None or
                    version is not None):
                raise ValueError(
                    "May not provide both channels and other parameters")
            self._validate_channels(channels)
            self._channels = channels
            self._fd = None
        elif fd is not None:
            if channels is not None:
                raise ValueError(
                    "May not provide both channels and other parameters")
            self._image = None
            self._fd = fd
            self._offset = offset
            self._size = size
            self._height = height
            self._width = width
            self._num_channels = num_channels
            self._depth = depth
            self._version = version
        else:
            self._channels = None
            self._fd = None

    @property
    def compression(self):
        "Type of compression. See `enums.Compression`."
        return self._compression

    @compression.setter
    def compression(self, value):
        if value not in list(enums.Compression):
            raise ValueError("invalid compression type")
        self._compression = value

    def _validate_channels(self, channels):
        if channels is None:
            return
        if len(channels.shape) != 3:
            raise ValueError("image must be a 3-dimensional array")
        if channels.dtype.kind != 'u':
            raise ValueError("image must have unsigned integer data type")

    @property
    def channels(self):
        if self._fd is None:
            return self._channels

        tell = self._fd.tell()
        self._fd.seek(self._offset)
        try:
            data = self._fd.read(self._size)
            image = codecs.decompress_image(
                data, self.compression,
                (self._height * self._num_channels, self._width),
                self._depth, self._version)
            return image.reshape(
                (self._num_channels, self._height, self._width))
        finally:
            self._fd.seek(tell)

    @property
    def shape(self):
        if self._fd is None:
            return self._channels.shape
        return self._shape

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        compression = fd.read(2)
        if compression == b'':
            raise IOError("Unexpected end of file")

        compression = struct.unpack('>H', compression)[0]
        util.log("compression: {}", enums.Compression(compression))

        offset = fd.tell()
        fd.seek(0, 2)
        size = fd.tell() - offset

        return cls(fd=fd, offset=offset, size=size, height=header.height,
                   width=header.width, num_channels=header.num_channels,
                   depth=header.depth, version=header.version,
                   compression=compression)

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'H', self.compression)

        if self._fd is None:
            if self.channels is None:
                channels = 0
            else:
                channels = self.channels
            codecs.compress_image(
                fd, channels, self.compression, header.shape,
                header.num_channels, header.depth, header.version)
        else:
            tell = self._fd.tell()
            try:
                self._fd.seek(self._offset)
                data = self._fd.read(self._size)
            finally:
                self._fd.seek(tell)
            fd.write(data)
