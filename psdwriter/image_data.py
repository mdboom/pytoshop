# -*- coding: utf-8 -*-


import struct


import traitlets as t


from . import enums
from . import util


class ImageData(t.HasTraits):
    def __init__(self, data, **kwargs):
        t.HasTraits.__init__(self, **kwargs)
        self._data = data

    compression = t.Enum(list(enums.Compression))

    def length(self, header):
        return len(self.data_length)

    def total_length(self, header):
        return 2 + self.length(header)

    @property
    def data(self):
        return self._data

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        compression = fd.read(2)
        if compression == b'':
            raise IOError("Unexpected end of file")

        compression = struct.unpack('>H', compression)[0]
        util.log("compression: {}", enums.Compression(compression))

        data = fd.read()

        return cls(data, compression=compression)

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'H', self.compression)
        fd.write(self.data)
