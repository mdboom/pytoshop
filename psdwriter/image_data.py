# -*- coding: utf-8 -*-


import struct


import traitlets as t


from . import enums
from . import util


class ImageData(util.DeferredLoad, t.HasTraits):
    def __init__(self, data, **kwargs):
        util.DeferredLoad.__init__(self, data)
        t.HasTraits.__init__(self, **kwargs)

    compression = t.Enum(list(enums.Compression))

    def length(self, header):
        return len(self.data_length)

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

        start = fd.tell()
        fd.seek(0, 2)
        end = fd.tell()
        data = (fd, start, end-start)

        return cls(data, compression=compression)

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'H', self.compression)
        fd.write(self.data)
