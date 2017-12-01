# -*- coding: utf-8 -*-


"""
The `ImageData` section.
"""


from __future__ import unicode_literals, absolute_import


import struct


import numpy as np  # NOQA


from . import codecs
from . import enums
from . import util


from typing import BinaryIO, Optional, Tuple, TYPE_CHECKING  # NOQA
if TYPE_CHECKING:
    from . import core  # NOQA


class ImageData(object):
    """
    Stores (non-layer) image data.
    """
    def __init__(self,
                 channels=None,      # type: Optional[np.ndarray]
                 fd=None,            # type: Optional[BinaryIO]
                 offset=None,        # type: Optional[int]
                 size=None,          # type: Optional[int]
                 height=None,        # type: Optional[int]
                 width=None,         # type: Optional[int]
                 num_channels=None,  # type: Optional[int]
                 depth=None,         # type: Optional[int]
                 version=None,       # type: Optional[int]
                 compression=enums.Compression.raw  # type: Optional[int]
                 ):  # type: (...) -> None
        case_a = channels is not None
        case_b = (fd is not None or offset is not None or size is not None or
                  height is not None or width is not None or
                  num_channels is not None or depth is not None or
                  version is not None)
        if case_a and case_b:
            raise ValueError(
                "May not provide both channels and other parameters")
        if case_a:
            self._validate_channels(channels)
        self.compression = compression
        self._channels = channels
        self._image = None
        self._fd = fd
        self._offset = offset
        self._size = size
        self._height = height
        self._width = width
        self._num_channels = num_channels
        self._depth = depth
        self._version = version
        self._shape = (0, 0)

    @property
    def compression(self):  # type: (...) -> int
        "Type of compression. See `enums.Compression`."
        return self._compression

    @compression.setter
    def compression(self, value):  # type: (int) -> None
        if value not in list(enums.Compression):  # type: ignore
            raise ValueError("invalid compression type")
        self._compression = value

    def _validate_channels(self, channels):
        # type: (Optional[np.ndarray]) -> None
        if channels is None:
            return
        if len(channels.shape) != 3:
            raise ValueError("image must be a 3-dimensional array")
        if channels.dtype.kind != 'u':
            raise ValueError("image must have unsigned integer data type")

    @property
    def channels(self):  # type: (...) -> np.ndarray
        if self._fd is None:
            return self._channels

        if (self._offset is None or
                self._size is None or
                self._height is None or
                self._width is None or
                self._num_channels is None or
                self._depth is None or
                self._version is None):
            raise RuntimeError("Internal inconsistency")

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
    def shape(self):  # type: (...) -> Tuple[int, int, int]
        if self._fd is None:
            if self._channels is None:
                raise RuntimeError("Internal inconsistency")
            return self._channels.shape
        if (self._num_channels is None or
                self._height is None or
                self._width is None):
            raise RuntimeError("Internal inconsistency")
        return (self._num_channels, self._height, self._width)

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        # type: (BinaryIO, core.Header) -> ImageData
        compression = fd.read(2)
        if compression == b'':
            raise IOError("Unexpected end of file")

        compression_val = struct.unpack(str('>H'), compression)[0]
        util.log("compression: {}", enums.Compression(compression_val))

        offset = fd.tell()
        fd.seek(0, 2)
        size = fd.tell() - offset

        return cls(fd=fd, offset=offset, size=size, height=header.height,
                   width=header.width, num_channels=header.num_channels,
                   depth=header.depth, version=header.version,
                   compression=compression_val)

    @util.trace_write
    def write(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
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
            if (self._offset is None or
                    self._size is None):
                raise RuntimeError("Internal inconsistency")

            tell = self._fd.tell()
            try:
                self._fd.seek(self._offset)
                data = self._fd.read(self._size)
            finally:
                self._fd.seek(tell)
            fd.write(data)
