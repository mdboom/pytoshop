# -*- coding: utf-8 -*-


import struct


import traitlets as t


from . import enums
from .util import write_value


class ImageData(t.HasTraits):
    compression = t.Enum(list(enums.Compression))
    # TODO: Defer loading of data
    data = t.Bytes()

    def length(self, header):
        return len(self.data)

    def total_length(self, header):
        return 2 + self.length(header)

    @classmethod
    def read(cls, fd, header):
        compression = fd.read(2)
        if compression == b'':
            return None

        compression = struct.unpack('>H', compression)[0]
        data = fd.read()

        return cls(
            compression=compression,
            data=data)

    def write(self, fd, header):
        write_value(fd, 'H', self.compression)
        fd.write(self.data)
