# -*- coding: utf-8 -*-


"""
The `ImageResources` section.

Image resource blocks are the basic building unit of several file
formats, including Photoshop's native file format, JPEG, and
TIFF. Image resources are used to store non-pixel data associated with
images, such as pen tool paths.
"""


from __future__ import unicode_literals, absolute_import


import six


import numpy as np
import traitlets as t


from . import docs
from . import enums
from . import util


class _ImageResourceBlockMeta(type(t.HasTraits)):
    """
    A metaclass that builds a mapping of subclasses.
    """
    mapping = {}

    def __new__(cls, name, parents, dct):
        new_cls = type(t.HasTraits).__new__(cls, name, parents, dct)

        if 'resource_id' in dct and isinstance(dct['resource_id'], int):
            if dct['resource_id'] in cls.mapping:
                raise ValueError(
                    "Duplicate resource_id '{}'".format(
                        dct['resource_id']))
            cls.mapping[dct['resource_id']] = new_cls

        return new_cls


@six.add_metaclass(_ImageResourceBlockMeta)
class ImageResourceBlock(t.HasTraits):
    """
    Stores a single image resource block.

    ``pytoshop`` currently doesn't deeply parse image resource
    blocks.  The raw data is merely retained for round-tripping.
    """
    name = t.Unicode(
        default_value='',
        max=255,
        help="Name of image resource."
    )

    def length(self, header):
        data_length = self.data_length(header)
        length = (
            4 + 2 +
            util.pascal_string_length(self.name, 2) +
            4 + data_length
        )
        if data_length % 2 != 0:
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

        util.log(
            "resource_id: {}, name: {}, data_length: {}",
            resource_id, name, data_length
        )

        new_cls = _ImageResourceBlockMeta.mapping.get(
            resource_id, GenericImageResourceBlock)
        start = fd.tell()
        result = new_cls.read_data(fd, resource_id, name, data_length, header)
        end = fd.tell()
        if end - start != data_length:
            raise ValueError("{} read the wrong amount".format(new_cls))

        if data_length % 2 != 0:
            fd.read(1)

        return result
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        fd.write(b'8BIM')
        util.write_value(fd, 'H', self.resource_id)
        util.write_pascal_string(fd, self.name, 2)
        length = self.data_length(header)
        util.write_value(fd, 'I', length)
        start = fd.tell()
        self.write_data(fd, header)
        end = fd.tell()
        if end - start != length:
            raise ValueError(
                "{} wrote the wrong amount".format(self.__class__))
        if length % 2 != 0:
            fd.write(b'\0')
    write.__doc__ = docs.write


class GenericImageResourceBlock(ImageResourceBlock):
    resource_id = t.Int(
        help="Type of image resource."
    )
    data = t.Bytes(
        max=(1 << 32),
        help="Raw data of image resource."
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        data = fd.read(length)
        return cls(resource_id=resource_id, name=name, data=data)

    def data_length(self, header):
        return len(self.data)

    @util.trace_write
    def write_data(self, fd, header):
        fd.write(self.data)


class LayersGroupInfo(ImageResourceBlock):
    resource_id = enums.ImageResourceID.layers_group_info
    group_ids = t.List(
        t.Int,
        help="Layer group ids"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, resource_id, name, length, header):
        data = fd.read(length)
        group_ids = np.frombuffer(data, '>u2').tolist()
        return cls(name=name, group_ids=group_ids)

    def data_length(self, header):
        return len(self.group_ids * 2)

    @util.trace_write
    def write_data(self, fd, header):
        data = np.array(self.group_ids, '>u2').tobytes()
        fd.write(data)


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

    def get_block(self, resource_id):
        """
        Get the first block with the given resource id.
        """
        for block in self.blocks:
            if block.resource_id == resource_id:
                return block
        return None

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        length = util.read_value(fd, 'I')
        end = fd.tell() + length

        util.log("length: {}, end: {}", length, end)

        blocks = []
        while fd.tell() < end:
            blocks.append(ImageResourceBlock.read(fd, header))

        if fd.tell() != end:
            raise ValueError(
                "read the wrong amount reading image resource blocks")

        return cls(blocks=blocks)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'I', self.length(header))
        for block in self.blocks:
            block.write(fd, header)
    write.__doc__ = docs.write
