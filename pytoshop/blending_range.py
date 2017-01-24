# -*- coding: utf-8 -*-


"""
Manage blending ranges.
"""


from __future__ import unicode_literals, absolute_import


import struct


import numpy as np
import traitlets as t


from . import docs
from . import util


class BlendingRange:
    """
    Blending range data.

    Comprises 2 black values and 2 white values.
    """
    def __init__(self, black0=0, black1=0, white0=0, white1=0, _values=None):
        if _values is not None:
            self._values = _values
        else:
            self._values = np.array(
                [black0, black1, white0, white1],
                np.uint8)

    @property
    def black0(self):
        return self._values[0]

    @black0.setter
    def black0(self, val):
        self._values[0] = val

    @property
    def black1(self):
        return self._values[1]

    @black1.setter
    def black1(self, val):
        self._values[1] = val

    @property
    def white0(self):
        return self._values[2]

    @white0.setter
    def white0(self, val):
        self._values[2] = val

    @property
    def white1(self):
        return self._values[3]

    @white1.setter
    def white1(self, val):
        self._values[3] = val

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        buf = fd.read(4)
        values = np.frombuffer(buf, np.uint8)

        util.log(
            "values: {}",
            values)

        return cls(_values=values)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        fd.write(self._values.tobytes())
    write.__doc__ = docs.write


class BlendingRangePair:
    """
    Blending range pair.

    The combination of a source and destination blending range.
    """
    def __init__(self, src=None, dst=None):
        if src is None:
            src = BlendingRange()
        if dst is None:
            dst = BlendingRange()
        self._src = src
        self._dst = dst

    @property
    def src(self):
        return self._src

    @src.setter
    def src(self, val):
        if not isinstance(val, BlendingRange):
            raise TypeError("src must be BlendingRange instance")
        self._src = val

    @property
    def dst(self):
        return self._dst

    @dst.setter
    def dst(self, val):
        if not isinstance(val, BlendingRange):
            raise TypeError("dst must be BlendingRange instance")
        self._dst = val

    def length(self, header):
        return 8
    length.__doc__ = docs.length

    def total_length(self, header):
        return self.length(header)
    total_length.__doc__ = docs.total_length

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        src = BlendingRange.read(fd, header)
        dst = BlendingRange.read(fd, header)

        return cls(src=src, dst=dst)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        self.src.write(fd, header)
        self.dst.write(fd, header)
    write.__doc__ = docs.write


class BlendingRanges(t.HasTraits):
    """
    All of the layer blending range data.

    Consists of a composite gray blend pair followed by N additional
    pairs.
    """
    composite_gray_blend = t.Instance(
        BlendingRangePair, allow_none=True,
        help="Composite gray `BlendingRangePair`."
    )
    channels = t.List(
        t.Instance(BlendingRangePair),
        help="List of additional `BlendingRangePair` instances."
    )

    def length(self, header):
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
    length.__doc__ = docs.length

    def total_length(self, header):
        return 4 + self.length(header)
    total_length.__doc__ = docs.total_length

    @classmethod
    @util.trace_read
    def read(cls, fd, header, num_channels):
        length = util.read_value(fd, 'I')
        end = fd.tell() + length
        util.log("length: {}, end: {}", length, end)
        if length == 0:
            return cls()

        composite_gray_blend = BlendingRangePair.read(fd, header)
        channels = []
        while fd.tell() < end:
            channels.append(BlendingRangePair.read(fd, header))

        fd.seek(end)

        return cls(
            composite_gray_blend=composite_gray_blend,
            channels=channels)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
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
