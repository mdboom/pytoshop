# -*- coding: utf-8 -*-


import struct


import traitlets as t


from . import enums
from .util import write_value, DeferredLoad


class ImageData(DeferredLoad, t.HasTraits):
    def __init__(self, data, **kwargs):
        DeferredLoad.__init__(self, data)
        t.HasTraits.__init__(self, **kwargs)

    compression = t.Enum(list(enums.Compression))

    def length(self, header):
        return len(self.data_length)

    def total_length(self, header):
        return 2 + self.length(header)

    @classmethod
    def read(cls, fd, header):
        compression = fd.read(2)
        if compression == b'':
            return None

        compression = struct.unpack('>H', compression)[0]
        start = fd.tell()
        fd.seek(0, 2)
        end = fd.tell()
        data = (fd, start, end-start)

        return cls(data, compression=compression)

    def write(self, fd, header):
        write_value(fd, 'H', self.compression)
        fd.write(self.data)
