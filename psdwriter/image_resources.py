# -*- coding: utf-8 -*-

import traitlets as t

from .util import read_pascal_string, write_pascal_string, \
    pascal_string_length, read_value, write_value, trace_read


class ImageResourceBlock(t.HasTraits):
    resource_id = t.Int()
    name = t.Bytes(max=255)
    data = t.Bytes(max=(1 << 32))

    def length(self, header):
        return 4 + 2 + pascal_string_length(self.name, 2) + 4 + len(self.data)

    total_length = length

    @classmethod
    @trace_read
    def read(cls, fd, header):
        signature = fd.read(4)
        if signature != b'8BIM':
            raise ValueError('Invalid image resource block signature')

        resource_id = read_value(fd, 'H')
        name = read_pascal_string(fd, 2)

        data_length = read_value(fd, 'I')
        data = fd.read(data_length)

        if data_length % 2 != 0:
            fd.read(1)

        return cls(resource_id=resource_id, name=name, data=data)

    def write(self, fd, header):
        fd.write(b'8BIM')
        write_value(fd, 'H', self.resource_id)
        write_pascal_string(fd, self.name, 2)
        write_value(fd, 'I', len(self.data))
        fd.write(self.data)
        if len(self.data) % 2 != 0:
            fd.write(b'\0')


class ImageResources(t.HasTraits):
    blocks = t.List(t.Instance(ImageResourceBlock))

    def length(self, header):
        return sum(block.total_length(header) for block in self.blocks)

    def total_length(self, header):
        return 4 + self.length(header)

    @classmethod
    @trace_read
    def read(cls, fd, header):
        length = read_value(fd, 'I')
        end = fd.tell() + length

        blocks = []
        while fd.tell() < end:
            blocks.append(ImageResourceBlock.read(fd, header))

        return cls(blocks=blocks)

    def write(self, fd, header):
        write_value(fd, 'I', self.length(header))
        for block in self.blocks:
            block.write(fd, header)
