# -*- coding: utf-8 -*-


import traitlets as t


from .util import read_value, write_value


class ColorModeData(t.HasTraits):
    data = t.Bytes()

    def length(self, header):
        return len(self.data)

    def total_length(self, header):
        return 4 + self.length(header)

    @classmethod
    def read(cls, fd, header):
        length = read_value(fd, 'I')
        data = fd.read(length)
        return cls(data=data)

    def write(self, fd, header):
        write_value(fd, 'I', self.length(header))
        fd.write(self.data)
