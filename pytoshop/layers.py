# -*- coding: utf-8 -*-


"""
Sections related to image layers.
"""


from __future__ import unicode_literals, absolute_import


import collections
import os


import numpy as np
import six


from . import blending_range
from . import codecs
from . import docs
from . import enums
from . import tagged_block
from . import util


class LayerMask(object):
    """
    Layer mask / adjustment layer data.
    """
    def __init__(self,
                 top=0, left=0, bottom=0, right=0,
                 default_color=False,
                 position_relative_to_layer=False,
                 layer_mask_disabled=False,
                 invert_layer_mask_when_blending=False,
                 user_mask_from_rendering_other_data=False,
                 user_mask_density=None,
                 user_mask_feather=None,
                 vector_mask_density=None,
                 vector_mask_feather=None,
                 real_flags=0,
                 real_user_mask_background=False,
                 real_top=0, real_left=0, real_bottom=0, real_right=0):
        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right
        self.default_color = default_color
        self.position_relative_to_layer = position_relative_to_layer
        self.layer_mask_disabled = layer_mask_disabled
        self.invert_layer_mask_when_blending = invert_layer_mask_when_blending
        self.user_mask_from_rendering_other_data = \
            user_mask_from_rendering_other_data
        self.user_mask_density = user_mask_density
        self.user_mask_feather = user_mask_feather
        self.vector_mask_density = vector_mask_density
        self.vector_mask_feather = vector_mask_feather
        self.real_flags = real_flags
        self.real_user_mask_background = real_user_mask_background
        self.real_top = real_top
        self.real_left = real_left
        self.real_bottom = real_bottom
        self.real_right = real_right

    @property
    def top(self):
        "Top of rectangle enclosing layer mask"
        return self._top

    @top.setter
    def top(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("top must be a 32-bit integer")
        self._top = value

    @property
    def left(self):
        "Left of rectangle enclosing layer mask"
        return self._left

    @left.setter
    def left(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("left must be a 32-bit integer")
        self._left = value

    @property
    def bottom(self):
        "Bottom of rectangle enclosing layer mask"
        return self._bottom

    @bottom.setter
    def bottom(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("bottom must be a 32-bit integer")
        self._bottom = value

    @property
    def right(self):
        "Right of rectangle enclosing layer mask"
        return self._right

    @right.setter
    def right(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("right must be a 32-bit integer")
        self._right = value

    @property
    def default_color(self):
        "Default color for mask"
        return self._default_color

    @default_color.setter
    def default_color(self, value):
        self._default_color = bool(value)

    @property
    def position_relative_to_layer(self):
        "position relative to layer"
        return self._position_relative_to_layer

    @position_relative_to_layer.setter
    def position_relative_to_layer(self, value):
        self._position_relative_to_layer = bool(value)

    @property
    def layer_mask_disabled(self):
        "Layer mask disabled"
        return self._layer_mask_disabled

    @layer_mask_disabled.setter
    def layer_mask_disabled(self, value):
        self._layer_mask_disabled = bool(value)

    @property
    def invert_layer_mask_when_blending(self):
        "Invert layer mask when blending (obsolete)"
        return self._invert_layer_mask_when_blending

    @invert_layer_mask_when_blending.setter
    def invert_layer_mask_when_blending(self, value):
        self._invert_layer_mask_when_blending = bool(value)

    @property
    def user_mask_from_rendering_other_data(self):
        """
        Indicates that the user mask actually came from rendering
        other data.
        """
        return self._user_mask_from_rendering_other_data

    @user_mask_from_rendering_other_data.setter
    def user_mask_from_rendering_other_data(self, value):
        self._user_mask_from_rendering_other_data = bool(value)

    @property
    def user_mask_density(self):
        "User mask density"
        return self._user_mask_density

    @user_mask_density.setter
    def user_mask_density(self, value):
        if (value is not None and
            (not isinstance(value, int) or
             value < 0 or value > 255)):
            raise ValueError(
                "user_mask_density must be an int in range 0 to 255 or None"
            )
        self._user_mask_density = value

    @property
    def user_mask_feather(self):
        "User mask feather"
        return self._user_mask_feather

    @user_mask_feather.setter
    def user_mask_feather(self, value):
        if (value is not None and
            (not isinstance(value, int) or
             value < 0 or value > 255)):
            raise ValueError(
                "user_mask_feather must be an int in range 0 to 255 or None"
            )
        self._user_mask_feather = value

    @property
    def vector_mask_density(self):
        "Vector mask density"
        return self._vector_mask_density

    @vector_mask_density.setter
    def vector_mask_density(self, value):
        if (value is not None and
            (not isinstance(value, int) or
             value < 0 or value > 255)):
            raise ValueError(
                "vector_mask_density must be an int in range 0 to 255 or None"
            )
        self._vector_mask_density = value

    @property
    def vector_mask_feather(self):
        "Vector mask feather"
        return self._vector_mask_feather

    @vector_mask_feather.setter
    def vector_mask_feather(self, value):
        if (value is not None and
            (not isinstance(value, int) or
             value < 0 or value > 255)):
            raise ValueError(
                "vector_mask_feather must be an int in range 0 to 255 or None"
            )
        self._vector_mask_feather = value

    @property
    def real_flags(self):
        return self._real_flags

    @real_flags.setter
    def real_flags(self, value):
        if not isinstance(value, int):
            raise TypeError("real_flags must be an int")
        self._real_flags = value

    @property
    def real_user_mask_background(self):
        return self._real_user_mask_background

    @real_user_mask_background.setter
    def real_user_mask_background(self, value):
        self._real_user_mask_background = bool(value)

    @property
    def real_top(self):
        return self._real_top

    @real_top.setter
    def real_top(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("real_top must be a 32-bit integer")
        self._real_top = value

    @property
    def real_left(self):
        return self._real_left

    @real_left.setter
    def real_left(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("real_left must be a 32-bit integer")
        self._real_left = value

    @property
    def real_bottom(self):
        return self._real_bottom

    @real_bottom.setter
    def real_bottom(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("real_bottom must be a 32-bit integer")
        self._real_bottom = value

    @property
    def real_right(self):
        return self._real_right

    @real_right.setter
    def real_right(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("real_right must be a 32-bit integer")
        self._real_right = value

    @property
    def width(self):
        """
        Width of the mask layer.
        """
        return self.right - self.left

    @property
    def height(self):
        """
        Height of the mask layer.
        """
        return self.bottom - self.top

    @property
    def shape(self):
        """
        Shape of the mask layer ``(height, width)``.
        """
        return (self.height, self.width)

    @property
    def real_width(self):
        """
        Real width of the mask layer.
        """
        return self.real_right - self.real_left

    @property
    def real_height(self):
        """
        Real height of the mask layer.
        """
        return self.real_bottom - self.real_top

    @property
    def real_shape(self):
        """
        Real shape of the mask layer ``(height, width)``.
        """
        return (self.real_height, self.real_width)

    def length(self, header):
        length = 16 + 1 + 1
        mask_flags = self._get_mask_flags()
        if mask_flags:
            length += 1
            if self.user_mask_density is not None:
                length += 1
            if self.user_mask_feather is not None:
                length += 8
            if self.vector_mask_density is not None:
                length += 1
            if self.vector_mask_feather is not None:
                length += 8
        length += 1 + 1 + 16
        return length
    length.__doc__ = docs.length

    def total_length(self, header):
        return 4 + self.length(header)
    total_length.__doc__ = docs.total_length

    def _get_mask_flags(self):
        return util.pack_bitflags(
            self.user_mask_density is not None,
            self.user_mask_feather is not None,
            self.vector_mask_density is not None,
            self.vector_mask_feather is not None)

    @classmethod
    @util.trace_read
    def read(cls, fd):
        length = util.read_value(fd, 'I')
        d = {}
        end = fd.tell() + length
        util.log("length: {}, end: {}", length, end)

        if length == 0:
            return cls(**d)

        top, left, bottom, right = util.read_value(fd, 'iiii')
        d['top'] = top
        d['left'] = left
        d['bottom'] = bottom
        d['right'] = right

        util.log("position: ({}, {}, {}, {})", top, left, bottom, right)

        d['default_color'] = bool(util.read_value(fd, 'B'))

        flags = util.read_value(fd, 'B')
        (d['position_relative_to_layer'],
         d['layer_mask_disabled'],
         d['invert_layer_mask_when_blending'],
         d['user_mask_from_rendering_other_data']) = util.unpack_bitflags(
             flags, 4)

        util.log("default_color: {}, flags: {}", d['default_color'], flags)

        if length == 20:
            util.log("done early")
            fd.seek(end)
            return cls(**d)

        if flags & 16:
            mask_parameters = util.read_value(fd, 'B')
            (has_user_mask_density,
             has_user_mask_feather,
             has_vector_mask_density,
             has_vector_mask_feather) = util.unpack_bitflags(
                 mask_parameters, 4)
            if has_user_mask_density:
                d['user_mask_density'] = util.read_value(fd, 'B')
            if has_user_mask_feather:
                d['user_mask_feather'] = util.read_value(fd, 'd')
            if has_vector_mask_density:
                d['vector_mask_density'] = util.read_value(fd, 'B')
            if has_vector_mask_feather:
                d['vector_mask_feather'] = util.read_value(fd, 'd')

        d['real_flags'] = util.read_value(fd, 'B')
        d['real_user_mask_background'] = bool(util.read_value(fd, 'B'))

        util.log(
            "real_flags: {}, real_user_mask_background: {}",
            d['real_flags'], d['real_user_mask_background']
        )

        top, left, bottom, right = util.read_value(fd, 'iiii')
        d['real_top'] = top
        d['real_left'] = left
        d['real_bottom'] = bottom
        d['real_right'] = right

        util.log(
            "real position: ({}, {}, {}, {})",
            top, left, bottom, right
        )

        fd.seek(end)

        return cls(**d)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        def write_rectangle(top, left, bottom, right):
            util.write_value(fd, 'iiii', top, left, bottom, right)

        def write_default_color(color):
            if color:
                util.write_value(fd, 'B', 255)
            else:
                util.write_value(fd, 'B', 0)

        util.write_value(fd, 'I', self.length(header))

        write_rectangle(self.top, self.left, self.bottom, self.right)
        write_default_color(self.default_color)

        mask_flags = self._get_mask_flags()

        flags = util.pack_bitflags(
            self.position_relative_to_layer,
            self.layer_mask_disabled,
            self.invert_layer_mask_when_blending,
            self.user_mask_from_rendering_other_data,
            mask_flags)

        util.write_value(fd, 'B', flags)

        if mask_flags:
            util.write_value(fd, 'B', mask_flags)

            if self.user_mask_density is not None:
                util.write_value(fd, 'B', self.user_mask_density)
            if self.user_mask_feather is not None:
                util.write_value(fd, 'd', self.user_make_feather)
            if self.vector_mask_density is not None:
                util.write_value(fd, 'B', self.vector_mask_density)
            if self.vector_mask_feather is not None:
                util.write_value(fd, 'd', self.vector_mask_feather)

        util.write_value(fd, 'B', self.real_flags)
        write_default_color(self.real_user_mask_background)
        write_rectangle(self.real_top, self.real_left,
                        self.real_bottom, self.real_right)
    write.__doc__ = docs.write


class ChannelImageData(object):
    """
    A single plane of channel image data.
    """
    def __init__(self, image=None, fd=None, offset=None, size=None,
                 shape=None, depth=None, version=None,
                 compression=enums.Compression.raw):
        self.compression = compression
        if image is not None:
            if (fd is not None or offset is not None or size is not None or
                    shape is not None or depth is not None or
                    version is not None):
                raise ValueError(
                    "May not provide both image and other parameters")
            self._image = image
        else:
            if image is not None:
                raise ValueError(
                    "May not provide both image and other parameters")
            self._image = None
            self._fd = fd
            self._offset = offset
            self._size = size
            self._shape = shape
            self._depth = depth
            self._version = version

    @property
    def compression(self):
        "Compression method. See `enums.Compression`."
        return self._compression

    @compression.setter
    def compression(self, value):
        if value not in list(enums.Compression):
            raise ValueError("Invalid compression type.")
        self._compression = value

    @property
    def image(self):
        if self._image is not None:
            return self._image
        tell = self._fd.tell()
        try:
            self._fd.seek(self._offset)
            data = self._fd.read(self._size)
            return codecs.decompress_image(
                data, self.compression, self._shape, self._depth,
                self._version)
        finally:
            self._fd.seek(tell)

    @image.setter
    def image(self, image):
        self._image = image

    @property
    def shape(self):
        if self._image is not None:
            return self._image.shape
        return self._shape

    @property
    def dtype(self):
        return np.dtype(codecs.color_depth_dtype_map[self._depth])

    @classmethod
    @util.trace_read
    def read(cls, fd, header, shape, size):
        compression = util.read_value(fd, 'H')
        util.log("compression: {}", enums.Compression(compression))
        offset = fd.tell()
        fd.seek(size, 1)

        return cls(fd=fd, offset=offset, size=size, shape=shape,
                   depth=header.depth, version=header.version,
                   compression=compression)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header, shape):
        start = fd.tell()
        util.write_value(fd, 'H', self.compression)
        if self._image is not None:
            codecs.compress_image(
                fd, self.image, self.compression, shape, 1,
                header.depth, header.version)
        else:
            if header.version == self._version:
                tell = self._fd.tell()
                try:
                    self._fd.seek(self._offset)
                    data = self._fd.read(self._size)
                finally:
                    self._fd.seek(tell)
                fd.write(data)
            else:
                codecs.compress_image(
                    fd, self.image, self.compression, shape, 1,
                    header.depth, header.version)
        return fd.tell() - start
    write.__doc__ = docs.write


class LayerRecord(object):
    """
    Layer record.

    There is one of these per logical layer in the file.
    """
    def __init__(self,
                 top=0, left=0, bottom=0, right=0,
                 blend_mode=enums.BlendMode.normal,
                 opacity=255,
                 clipping=False,
                 transparency_protected=False,
                 visible=True,
                 pixel_data_irrelevant=False,
                 name='',
                 channels={},
                 blocks=[]):
        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right
        self.blend_mode = blend_mode
        self.opacity = opacity
        self.clipping = clipping
        self.transparency_protected = transparency_protected
        self.visible = visible
        self.pixel_data_irrelevant = pixel_data_irrelevant
        self.name = name
        self.channels = channels
        self.blocks = blocks

    @property
    def top(self):
        "Top of rectangle enclosing layer"
        return self._top

    @top.setter
    def top(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("top must be a 32-bit integer")
        self._top = value

    @property
    def left(self):
        "Left of rectangle enclosing layer"
        return self._left

    @left.setter
    def left(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("left must be a 32-bit integer")
        self._left = value

    @property
    def bottom(self):
        "Bottom of rectangle enclosing layer"
        return self._bottom

    @bottom.setter
    def bottom(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("bottom must be a 32-bit integer")
        self._bottom = value

    @property
    def right(self):
        "Right of rectangle enclosing layer"
        return self._right

    @right.setter
    def right(self, value):
        if (not isinstance(value, int) or
                value < -(1 << 31) or value > (1 << 31)):
            raise ValueError("right must be a 32-bit integer")
        self._right = value

    @property
    def blend_mode(self):
        "Blend mode. See `enums.BlendMode`"
        return self._blend_mode

    @blend_mode.setter
    def blend_mode(self, value):
        if value not in list(enums.BlendMode):
            raise ValueError("Invalid blend mode.")
        self._blend_mode = value

    @property
    def opacity(self):
        "Opacity. 0=transparent, 255=opaque"
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        if not isinstance(value, int) or value < 0 or value > 255:
            raise ValueError("opacity must be an int in range 0 to 255")
        self._opacity = value

    @property
    def clipping(self):
        "Clipping. False=base, True=non-base"
        return self._clipping

    @clipping.setter
    def clipping(self, value):
        self._clipping = bool(value)

    @property
    def transparency_protected(self):
        "Transparency protected"
        return self._transparency_protected

    @transparency_protected.setter
    def transparency_protected(self, value):
        self._transparency_protected = bool(value)

    @property
    def visible(self):
        "Visible"
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = bool(value)

    @property
    def pixel_data_irrelevant(self):
        "Pixel data is irrelevant to appearance of document"
        return self._pixel_data_irrelevant

    @pixel_data_irrelevant.setter
    def pixel_data_irrelevant(self, value):
        self._pixel_data_irrelevant = bool(value)

    @property
    def name(self):
        "Name of layer"
        return self._name

    @name.setter
    def name(self, value):
        if isinstance(value, bytes):
            value = value.decode('ascii')

        if (not isinstance(value, six.text_type) or
                len(value) > 255):
            raise ValueError("name must be unicode string of length < 255")
        self._name = value

    @property
    def channels(self):
        "Dictionary from `enums.ChannelId` to `ChannelImageData`."
        return self._channels

    @channels.setter
    def channels(self, value):
        if not isinstance(value, dict):
            raise TypeError("channels must be a dict")

        for key, val in value.items():
            enums.ChannelId(key)

            if not isinstance(val, ChannelImageData):
                raise ValueError(
                    "Each channel must be ChannelImageData instance")

        value = collections.OrderedDict(
            sorted([(k, v) for (k, v) in value.items()]))

        self._channels = value

    @property
    def blocks(self):
        """
        List of `tagged_block.TaggedBlock` items with additional
        information about this layer.
        """
        return self._blocks

    @blocks.setter
    def blocks(self, value):
        util.assert_is_list_of(value, tagged_block.TaggedBlock)
        self._blocks = value

    @property
    def mask(self):
        if hasattr(self, '_mask'):
            return self._mask
        else:
            if hasattr(self, '_mask_offset'):
                start = self._fd.tell()
                try:
                    self._fd.seek(self._mask_offset)
                    self._mask = LayerMask.read(self._fd)
                finally:
                    self._fd.seek(start)
                del self._mask_offset
                return self._mask
            else:
                self._mask = LayerMask()
                return self._mask

    @mask.setter
    def mask(self, mask):
        if not isinstance(mask, LayerMask):
            raise TypeError("Must be a LayerMask instance")
        self._mask = mask

    @property
    def blending_ranges(self):
        if hasattr(self, '_blending_ranges'):
            return self._blending_ranges
        else:
            if hasattr(self, '_blending_ranges_offset'):
                start = self._fd.tell()
                try:
                    self._fd.seek(self._blending_ranges_offset)
                    self._blending_ranges = blending_range.BlendingRanges.read(
                        self._fd, len(self.channels))
                finally:
                    self._fd.seek(start)
                return self._blending_ranges
            else:
                self._blending_ranges = blending_range.BlendingRanges()
                return self._blending_ranges

    @blending_ranges.setter
    def blending_ranges(self, blending_ranges):
        if not isinstance(blending_ranges, blending_range.BlendingRanges):
            raise TypeError("Must be a BlendingRanges instance")
        self._blending_ranges = blending_ranges

    @property
    def width(self):
        """
        Width of the layer.
        """
        return self.right - self.left

    @property
    def height(self):
        """
        Height of the layer.
        """
        return self.bottom - self.top

    @property
    def shape(self):
        """
        Shape of the layer ``(height, width)``.
        """
        return (self.height, self.width)

    @property
    def blocks_map(self):
        """
        A mapping from tagged block codes to
        `tagged_block.TaggedBlock` instances.

        This is a convenience to more easily get associated tagged
        blocks.
        """
        return dict((x.code, x) for x in self.blocks)

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        top, left, bottom, right = util.read_value(fd, 'iiii')

        util.log("position: ({}, {}, {}, {})", top, left, bottom, right)

        num_channels = util.read_value(fd, 'H')
        channel_ids = []
        channel_data_lengths = []
        if header.version == 1:
            fmt = 'hI'
        else:
            fmt = 'hQ'
        for i in range(num_channels):
            channel_id, data_length = util.read_value(fd, fmt)
            channel_ids.append(channel_id)
            channel_data_lengths.append(data_length)

        util.log(
            "num_channels: {}, channel_ids: {}, channel_data_lengths: {}",
            num_channels, channel_ids, channel_data_lengths
        )

        (blend_mode_signature, blend_mode, opacity, clipping, flags, _,
         extra_length) = util.read_value(fd, '4s4sBBBBI')
        if blend_mode_signature != b'8BIM':
            raise ValueError(
                "Invalid blend mode signature '{}'".format(
                    blend_mode_signature))

        clipping = bool(clipping)
        (transparency_protected,
         visible,
         _,
         _,
         pixel_data_irrelevant) = util.unpack_bitflags(flags, 5)
        visible = not visible

        util.log(
            "blend_mode: {}, opacity: {}, clipping: {}, flags: {}",
            blend_mode, opacity, clipping, flags
        )

        end = fd.tell() + extra_length

        util.log("extra_length: {}, end: {}", extra_length, end)

        mask_offset = fd.tell()
        mask_length = util.read_value(fd, 'I')
        fd.seek(mask_length, os.SEEK_CUR)

        blending_ranges_offset = fd.tell()
        blending_ranges_length = util.read_value(fd, 'I')
        fd.seek(blending_ranges_length, os.SEEK_CUR)

        name = util.read_pascal_string(fd, 4)

        util.log("name: {}", name)

        blocks = []
        while fd.tell() < end:
            blocks.append(
                tagged_block.TaggedBlock.read(fd, header))
        fd.seek(end)

        result = cls(
            top=top,
            left=left,
            bottom=bottom,
            right=right,
            blend_mode=blend_mode,
            opacity=opacity,
            clipping=clipping,
            transparency_protected=transparency_protected,
            visible=visible,
            pixel_data_irrelevant=pixel_data_irrelevant,
            name=name,
            blocks=blocks
        )

        result._channel_data_lengths = channel_data_lengths
        result._channel_ids = channel_ids
        result._mask_offset = mask_offset
        result._blending_ranges_offset = blending_ranges_offset
        result._fd = fd
        return result
    read.__func__.__doc__ = docs.read

    def read_channel_data(self, fd, header):
        """
        Read the `ChannelImageData` for this layer.
        """
        channels = collections.OrderedDict()
        for channel_id, channel_length in zip(
                self._channel_ids, self._channel_data_lengths):
            if channel_id == enums.ChannelId.user_layer_mask:
                shape = self.mask.shape
            elif channel_id == enums.ChannelId.real_user_layer_mask:
                shape = self.mask.real_shape
            else:
                shape = self.shape
            channels[channel_id] = ChannelImageData.read(
                fd, header, shape, channel_length - 2)
        self._channels = channels

    @util.trace_write
    def write(self, fd, header):
        util.write_value(
            fd, 'iiii',
            self.top, self.left, self.bottom, self.right
        )
        util.write_value(fd, 'H', len(self.channels))
        self.channel_lengths_offset = fd.tell()
        if header.version == 1:
            fd.seek(6 * len(self.channels), 1)
        else:
            fd.seek(10 * len(self.channels), 1)
        flags = util.pack_bitflags(
            self.transparency_protected,
            not self.visible,
            False,
            True,
            self.pixel_data_irrelevant)
        extra_length = (
            self.mask.total_length(header) +
            self.blending_ranges.total_length(header) +
            util.pascal_string_length(self.name, 4) +
            sum(x.total_length(header) for x in self.blocks)
        )
        util.write_value(
            fd, '4s4sBBBBI', b'8BIM', self.blend_mode, self.opacity,
            int(self.clipping), flags, 0, extra_length)
        self.mask.write(fd, header)
        self.blending_ranges.write(fd, header)
        util.write_pascal_string(fd, self.name, 4)
        for block in self.blocks:
            block.write(fd, header)
    write.__doc__ = docs.write

    def write_channel_data(self, fd, header):
        """
        Write the `ChannelImageData` for this layer.
        """
        lengths = []
        for channel_id, data in self.channels.items():
            if channel_id == enums.ChannelId.user_layer_mask:
                shape = self.mask.shape
            elif channel_id == enums.ChannelId.real_user_layer_mask:
                shape = self.mask.real_shape
            else:
                shape = self.shape
            lengths.append(data.write(fd, header, shape))

        offset = fd.tell()
        fd.seek(self.channel_lengths_offset)
        if header.version == 1:
            fmt = 'hI'
        else:
            fmt = 'hQ'
        for channel_id, length in zip(self.channels.keys(), lengths):
            util.write_value(fd, fmt, channel_id, length)
        fd.seek(offset)


class LayerInfo(object):
    """
    A set of `LayerRecord` instances.
    """
    def __init__(self, layer_records=[], use_alpha_channel=False):
        self.layer_records = layer_records
        self.use_alpha_channel = use_alpha_channel

    @property
    def layer_records(self):
        "List of `LayerRecord` instances"
        return self._layer_records

    @layer_records.setter
    def layer_records(self, value):
        util.assert_is_list_of(value, LayerRecord)
        self._layer_records = value

    @property
    def use_alpha_channel(self):
        """
        Indicates that the first channel contains transparency data
        for the merged result.
        """
        return self._use_alpha_channel

    @use_alpha_channel.setter
    def use_alpha_channel(self, value):
        self._use_alpha_channel = bool(value)

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        if header.version == 1:
            length = util.read_value(fd, 'I')
        else:
            length = util.read_value(fd, 'Q')
        end = fd.tell() + length

        util.log("length: {}, end: {}", length, end)

        if length > 0:
            layer_count = util.read_value(fd, 'h')
            if layer_count < 0:
                layer_count = abs(layer_count)
                use_alpha_channel = True
            else:
                use_alpha_channel = False

            util.log("layer_count: {}, use_alpha_channel: {}",
                     layer_count, use_alpha_channel)

            layer_records = [
                LayerRecord.read(fd, header) for i in range(layer_count)
            ]
            for layer in layer_records:
                layer.read_channel_data(fd, header)

            fd.seek(end)

            return cls(
                layer_records=layer_records,
                use_alpha_channel=use_alpha_channel)
        else:
            return cls()
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        start = fd.tell()
        if header.version == 1:
            fd.seek(4, 1)
        else:
            fd.seek(8, 1)

        layer_count = len(self.layer_records)
        if layer_count == 0:
            return
        if self.use_alpha_channel:
            layer_count *= -1
        util.write_value(fd, 'h', layer_count)
        for layer in self.layer_records:
            layer.write(fd, header)
        for layer in self.layer_records:
            layer.write_channel_data(fd, header)

        end = fd.tell()
        fd.seek(start)
        if header.version == 1:
            util.write_value(fd, 'I', end - start - 4)
        else:
            util.write_value(fd, 'Q', end - start - 8)
        fd.seek(end)
    write.__doc__ = docs.write


class GlobalLayerMaskInfo(object):
    """
    Global layer mask info.
    """
    def __init__(self,
                 overlay_color_space=b'\0' * 10,
                 opacity=100,
                 kind=enums.LayerMaskKind.use_value_stored_per_layer):
        self.overlay_color_space = overlay_color_space
        self.opacity = opacity
        self.kind = kind

    @property
    def overlay_color_space(self):
        "Undocumented"
        return self._overlay_color_space

    @overlay_color_space.setter
    def overlay_color_space(self, value):
        if not isinstance(value, bytes) or len(value) != 10:
            raise ValueError(
                "overlay_color_space must be a length 10 bytes string"
            )
        self._overlay_color_space = value

    @property
    def opacity(self):
        "Opacity. 0=transparent, 100=opaque"
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > 100):
            raise ValueError("opacity must be an int in the range 0 to 100")
        self._opacity = value

    @property
    def kind(self):
        "Layer mask kind. See `enums.LayerMaskKind`"
        return self._kind

    @kind.setter
    def kind(self, value):
        if value not in list(enums.LayerMaskKind):
            raise ValueError("Invalid layer mask kind")
        self._kind = value

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        length = util.read_value(fd, 'I')
        end = fd.tell() + length
        util.log("length: {}, end: {}", length, end)
        if length == 0:
            return cls()

        overlay_color_space, opacity, kind = util.read_value(fd, '10sHB')

        util.log(
            "overlay_color_space: {}, opacity: {}, kind: {}",
            overlay_color_space, opacity, kind
        )

        fd.seek(end)

        return cls(
            overlay_color_space=overlay_color_space,
            opacity=opacity,
            kind=kind)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        util.write_value(
            fd, 'I10sHB3s', 16, self.overlay_color_space, self.opacity,
            self.kind, b'\0\0\0'
        )
    write.__doc__ = docs.write


class LayerAndMaskInfo(object):
    """
    Layer and mask information section.
    """
    def __init__(self,
                 layer_info=None,
                 global_layer_mask_info=None,
                 additional_layer_info=[]):
        if layer_info is None:
            layer_info = LayerInfo()
        self.layer_info = layer_info
        self.global_layer_mask_info = global_layer_mask_info
        self.additional_layer_info = additional_layer_info

    @property
    def layer_info(self):
        "Layer info. See `LayerInfo`."
        return self._layer_info

    @layer_info.setter
    def layer_info(self, value):
        if not isinstance(value, LayerInfo):
            raise TypeError("layer_info must be LayerInfo instance.")
        self._layer_info = value

    @property
    def global_layer_mask_info(self):
        "Global layer mask info. See `GlobalLayerMaskInfo`."
        return self._global_layer_mask_info

    @global_layer_mask_info.setter
    def global_layer_mask_info(self, value):
        if value is not None and not isinstance(value, GlobalLayerMaskInfo):
            raise TypeError(
                "global_layer_mask_info must be GlobalLayerMaskInfo "
                "instance or None"
            )
        self._global_layer_mask_info = value

    @property
    def additional_layer_info(self):
        "List of additional layer info. See `TaggedBlock`."
        return self._additional_layer_info

    @additional_layer_info.setter
    def additional_layer_info(self, value):
        util.assert_is_list_of(value, tagged_block.TaggedBlock)
        self._additional_layer_info = value

    @property
    def additional_layer_info_map(self):
        """
        A mapping from tagged block codes to
        `tagged_block.TaggedBlock` instances.

        This is a convenience to more easily get associated tagged
        blocks.
        """
        return dict((x.code, x) for x in self.additional_layer_info)

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        if header.version == 1:
            length = util.read_value(fd, 'I')
        else:
            length = util.read_value(fd, 'Q')
        end = fd.tell() + length

        util.log("length: {}, end: {}", length, end)

        layer_info = LayerInfo.read(fd, header)

        global_layer_mask_info = None
        additional_layer_info = []
        if fd.tell() < end:
            global_layer_mask_info = GlobalLayerMaskInfo.read(fd, header)

            while fd.tell() < end:
                additional_layer_info.append(
                    tagged_block.TaggedBlock.read(fd, header, 4))

        return cls(layer_info=layer_info,
                   global_layer_mask_info=global_layer_mask_info,
                   additional_layer_info=additional_layer_info)
    read.__func__.__doc__ = docs.read

    @util.trace_write
    def write(self, fd, header):
        start = fd.tell()

        if header.version == 1:
            fd.seek(4, 1)
        else:
            fd.seek(8, 1)

        self.layer_info.write(fd, header)
        if (self.global_layer_mask_info is not None or
                len(self.additional_layer_info)):
            if self.global_layer_mask_info is None:
                global_layer_mask_info = GlobalLayerMaskInfo()
            else:
                global_layer_mask_info = self.global_layer_mask_info
            global_layer_mask_info.write(fd, header)
            for layer_info in self.additional_layer_info:
                layer_info.write(fd, header, 4)

        end = fd.tell()
        fd.seek(start)
        if header.version == 1:
            util.write_value(fd, 'I', end - start - 4)
        else:
            util.write_value(fd, 'Q', end - start - 8)
        fd.seek(end)
    write.__doc__ = docs.write
