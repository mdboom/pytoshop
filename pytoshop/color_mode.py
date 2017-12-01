# -*- coding: utf-8 -*-


"""
The `ColorModeData` section.
"""


from __future__ import unicode_literals, absolute_import


from . import docs
from . import util


from typing import BinaryIO, TYPE_CHECKING  # NOQA
if TYPE_CHECKING:
    from . import core  # NOQA


class ColorModeData(object):
    """
    Color mode data section.

    Only indexed color and duotone (see `core.Header.color_mode`) have
    color mode data.

    Indexed color images: length is 768; color data contains the color
    table for the image, in non-interleaved order.

    Duotone images: color data contains the duotone specification (the
    format of which is not documented). Other applications that read
    Photoshop files can treat a duotone image as a gray image, and
    just preserve the contents of the duotone information when reading
    and writing the file.

    Note that ``pytoshop`` doesn't do anything meaningful for color
    mode data, and only stores the raw bytes in order to round-trip.
    """
    def __init__(self,
                 data=b''  # type: bytes
                 ):  # type: (...) -> None
        self.data = data

    @property
    def data(self):  # type: (...) -> bytes
        return self._data

    @data.setter
    def data(self, value):  # type: (bytes) -> None
        if not isinstance(value, bytes):
            raise TypeError('data must be a bytes instance')
        self._data = value

    def length(self, header):  # type: (core.Header) -> int
        return len(self.data)
    length.__doc__ = docs.length  # type: ignore

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        # type: (BinaryIO, core.Header) -> ColorModeData
        length = util.read_value(fd, 'I')
        util.log("length: {}", length)
        data = fd.read(length)
        return cls(data=data)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'I', self.length(header))
        fd.write(self.data)
    write.__doc__ = docs.write
