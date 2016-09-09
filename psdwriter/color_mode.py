# -*- coding: utf-8 -*-


import traitlets as t


from .util import read_value, write_value, trace_read, log, trace_write


class ColorModeData(t.HasTraits):
    data = t.Bytes()

    def length(self, header):
        return len(self.data)

    def total_length(self, header):
        return 4 + self.length(header)

    @classmethod
    @trace_read
    def read(cls, fd, header):
        length = read_value(fd, 'I')
        log("length: {}", length)
        data = fd.read(length)
        return cls(data=data)

    @trace_write
    def write(self, fd, header):
        write_value(fd, 'I', self.length(header))
        fd.write(self.data)
