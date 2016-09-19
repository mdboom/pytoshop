# -*- coding: utf-8 -*-


"""
Manage blending ranges.
"""


import struct


import traitlets as t


from . import docs
from . import util


class BlendingRange(t.HasTraits):
    """
    Blending range data.

    Comprises 2 black values and 2 white values.
    """
    black0 = t.Int(min=0, max=255)
    black1 = t.Int(min=0, max=255)
    white0 = t.Int(min=0, max=255)
    white1 = t.Int(min=0, max=255)

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        black0, black1, white0, white1 = struct.unpack('>BBBB', fd.read(4))

        util.log(
            "black: ({}, {}), white: ({}, {})",
            black0, black1, white0, white1)

        return cls(
            black0=black0,
            black1=black1,
            white0=white0,
            white1=white1)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        fd.write(struct.pack(
            '>BBBB', self.black0, self.black1, self.white0, self.white1))
    write.__doc__ = docs.write


class BlendingRangePair(t.HasTraits):
    """
    Blending range pair.

    The combination of a source and destination blending range.
    """
    src = t.Instance(
        BlendingRange,
        help="Source `BlendingRange`"
    )
    dst = t.Instance(
        BlendingRange,
        help="Destination `BlendingRange`"
    )

    @t.default('src')
    def _default_src(self):
        return BlendingRange()

    @t.default('dst')
    def _default_dst(self):
        return BlendingRange()

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

        return cls(src=src,
                   dst=dst)
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
