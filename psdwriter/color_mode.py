# -*- coding: utf-8 -*-


import traitlets as t


from . import util


class ColorModeData(t.HasTraits):
    data = t.Bytes()

    def length(self, header):
        return len(self.data)

    def total_length(self, header):
        return 4 + self.length(header)

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        length = util.read_value(fd, 'I')
        util.log("length: {}", length)
        data = fd.read(length)
        return cls(data=data)

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'I', self.length(header))
        fd.write(self.data)
