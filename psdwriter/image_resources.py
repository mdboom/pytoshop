# -*- coding: utf-8 -*-


"""
The `ImageResources` section.

Image resource blocks are the basic building unit of several file
formats, including Photoshop's native file format, JPEG, and
TIFF. Image resources are used to store non-pixel data associated with
images, such as pen tool paths.
"""


import traitlets as t


from . import docs
from . import util


class ImageResourceBlock(t.HasTraits):
    """
    Stores a single image resource block.

    ``psdwriter`` currently doesn't deeply parse image resource
    blocks.  The raw data is merely retained for round-tripping.
    """
    resource_id = t.Int(
        help="Type of image resource."
    )
    name = t.Unicode(
        max=255,
        help="Name of image resource."
    )
    data = t.Bytes(
        max=(1 << 32),
        help="Raw data of image resource."
    )

    def length(self, header):
        length = (4 + 2 +
                  util.pascal_string_length(self.name, 2) +
                  4 + len(self.data))
        if len(self.data) % 2 != 0:
            length += 1
        return length
    length.__doc__ = docs.length

    def total_length(self, header):
        return self.length(header)
    total_length.__doc__ = docs.total_length

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        signature = fd.read(4)
        if signature != b'8BIM':
            raise ValueError('Invalid image resource block signature')

        resource_id = util.read_value(fd, 'H')
        name = util.read_pascal_string(fd, 2)

        data_length = util.read_value(fd, 'I')
        data = fd.read(data_length)

        util.log("resource_id: {}, name: {}, data_length: {}",
                 resource_id, name, data_length)

        if data_length % 2 != 0:
            fd.read(1)

        return cls(resource_id=resource_id, name=name, data=data)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        fd.write(b'8BIM')
        util.write_value(fd, 'H', self.resource_id)
        util.write_pascal_string(fd, self.name, 2)
        util.write_value(fd, 'I', len(self.data))
        fd.write(self.data)
        if len(self.data) % 2 != 0:
            fd.write(b'\0')
    write.__doc__ = docs.write


class ImageResources(t.HasTraits):
    """
    The image resource block section.
    """
    blocks = t.List(
        t.Instance(ImageResourceBlock),
        help="List of all `ImageResourceBlock` items."
    )

    def length(self, header):
        return sum(block.total_length(header) for block in self.blocks)
    length.__doc__ = docs.length

    def total_length(self, header):
        return 4 + self.length(header)
    total_length.__doc__ = docs.total_length

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        length = util.read_value(fd, 'I')
        end = fd.tell() + length

        util.log("length: {}, end: {}", length, end)

        blocks = []
        while fd.tell() < end:
            blocks.append(ImageResourceBlock.read(fd, header))

        return cls(blocks=blocks)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'I', self.length(header))
        for block in self.blocks:
            block.write(fd, header)
    write.__doc__ = docs.write
