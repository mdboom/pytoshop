# -*- coding: utf-8 -*-


"""
Manage blending ranges.
"""


from __future__ import unicode_literals, absolute_import


import numpy as np


from . import docs
from . import util


from typing import BinaryIO, List, Optional, TYPE_CHECKING  # NOQA
if TYPE_CHECKING:
    from . import core  # NOQA


class BlendingRange(object):
    """
    Blending range data.

    Comprises 2 black values and 2 white values.
    """
    def __init__(self,
                 black0=0,     # type: int
                 black1=0,     # type: int
                 white0=0,     # type: int
                 white1=0,     # type: int
                 _values=None  # type: Optional[np.ndarray]
                 ):  # type: (...) -> None
        if _values is not None:
            self._values = _values
        else:
            self._values = np.array(
                [black0, black1, white0, white1],
                np.uint8)

    @property
    def black0(self):  # type: (...) -> int
        return self._values[0]

    @black0.setter
    def black0(self, val):  # type: (int) -> None
        self._values[0] = val

    @property
    def black1(self):  # type: (...) -> int
        return self._values[1]

    @black1.setter
    def black1(self, val):  # type: (int) -> None
        self._values[1] = val

    @property
    def white0(self):  # type: (...) -> int
        return self._values[2]

    @white0.setter
    def white0(self, val):  # type: (int) -> None
        self._values[2] = val

    @property
    def white1(self):  # type: (...) -> int
        return self._values[3]

    @white1.setter
    def white1(self, val):  # type: (int) -> None
        self._values[3] = val

    @classmethod
    @util.trace_read
    def read(cls, fd):
        # type: (BinaryIO) -> BlendingRange
        buf = fd.read(4)
        values = np.frombuffer(buf, np.uint8)

        util.log(
            "values: {}",
            values)

        return cls(_values=values)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        fd.write(self._values.tobytes())
    write.__doc__ = docs.write


class BlendingRangePair(object):
    """
    Blending range pair.

    The combination of a source and destination blending range.
    """
    def __init__(self,
                 src=None,  # type: Optional[BlendingRange]
                 dst=None   # type: Optional[BlendingRange]
                 ):  # type: (...) -> None
        if src is None:
            src = BlendingRange()
        if dst is None:
            dst = BlendingRange()
        self._src = src
        self._dst = dst

    @property
    def src(self):  # type: (...) -> BlendingRange
        return self._src

    @src.setter
    def src(self, val):  # type: (BlendingRange) -> None
        if not isinstance(val, BlendingRange):
            raise TypeError("src must be BlendingRange instance")
        self._src = val

    @property
    def dst(self):  # type: (...) -> BlendingRange
        return self._dst

    @dst.setter
    def dst(self, val):  # type: (BlendingRange) -> None
        if not isinstance(val, BlendingRange):
            raise TypeError("dst must be BlendingRange instance")
        self._dst = val

    def length(self, header):  # type: (core.Header) -> int
        return 8
    length.__doc__ = docs.length  # type: ignore

    def total_length(self, header):  # type: (core.Header) -> int
        return self.length(header)
    total_length.__doc__ = docs.total_length  # type: ignore

    @classmethod
    @util.trace_read
    def read(cls, fd):
        # type: (BinaryIO) -> BlendingRangePair
        src = BlendingRange.read(fd)
        dst = BlendingRange.read(fd)

        return cls(src=src, dst=dst)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        self.src.write(fd, header)
        self.dst.write(fd, header)
    write.__doc__ = docs.write


class BlendingRanges(object):
    """
    All of the layer blending range data.

    Consists of a composite gray blend pair followed by N additional
    pairs.
    """
    def __init__(
            self,
            composite_gray_blend=None,  # type: Optional[BlendingRangePair]
            channels=None  # type: Optional[List[BlendingRangePair]]
            ):  # type: (...) -> None
        self.composite_gray_blend = composite_gray_blend
        if channels is None:
            channels = []
        self.channels = channels

    @property
    def composite_gray_blend(self):  # type: (...) -> BlendingRangePair
        """Composite gray `BlendingRangePair`."""
        return self._composite_gray_blend

    @composite_gray_blend.setter
    def composite_gray_blend(self, value):
        # type: (BlendingRangePair) -> None
        if (value is not None and
                not isinstance(value, BlendingRangePair)):
            raise TypeError(
                "composite_gray_blend must be None or BlendingRangePair "
                "instance."
            )
        self._composite_gray_blend = value

    @property
    def channels(self):  # type: (...) -> List[BlendingRangePair]
        """List of additional `BlendingRangePair` instances."""
        return self._channels

    @channels.setter
    def channels(self, value):
        # type: (List[BlendingRangePair]) -> None
        util.assert_is_list_of(value, BlendingRangePair)
        self._channels = value

    def length(self, header):  # type: (core.Header) -> int
        if (self.composite_gray_blend is not None or
                len(self.channels)):
            if self.composite_gray_blend is None:
                composite_gray_blend = BlendingRangePair()
            else:
                composite_gray_blend = self.composite_gray_blend
            return (
                composite_gray_blend.total_length(header) +
                sum(x.total_length(header) for x in self.channels))
        return 0
    length.__doc__ = docs.length  # type: ignore

    def total_length(self, header):  # type: (core.Header) -> int
        return 4 + self.length(header)
    total_length.__doc__ = docs.total_length  # type: ignore

    @classmethod
    @util.trace_read
    def read(cls, fd, num_channels):
        # type: (BinaryIO, int) -> BlendingRanges
        length = util.read_value(fd, 'I')
        end = fd.tell() + length
        util.log("length: {}, end: {}", length, end)
        if length == 0:
            return cls()

        composite_gray_blend = BlendingRangePair.read(fd)
        channels = []
        while fd.tell() < end:
            channels.append(BlendingRangePair.read(fd))

        fd.seek(end)

        return cls(
            composite_gray_blend=composite_gray_blend,
            channels=channels)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'I', self.length(header))
        if (self.composite_gray_blend is not None or
                len(self.channels)):
            if self.composite_gray_blend is None:
                composite_gray_blend = BlendingRangePair()
            else:
                composite_gray_blend = self.composite_gray_blend
            composite_gray_blend.write(fd, header)
            for channel in self.channels:
                channel.write(fd, header)
    write.__doc__ = docs.write
