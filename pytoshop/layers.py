# -*- coding: utf-8 -*-


"""
Sections related to image layers.
"""


from __future__ import unicode_literals, absolute_import


import collections
import struct


import numpy as np
import traitlets as t


from . import blending_range
from . import codecs
from . import docs
from . import enums
from . import tagged_block
from . import util


class LayerMask(t.HasTraits):
    """
    Layer mask / adjustment layer data.
    """
    top = t.Int(
        help="Top of rectangle enclosing layer mask"
    )
    left = t.Int(
        help="Left of rectangle enclosing layer mask"
    )
    bottom = t.Int(
        help="Bottom of rectangle enclosing layer mask"
    )
    right = t.Int(
        help="Right of rectangle enclosing layer mask"
    )
    default_color = t.Bool(
        False,
        help="Default color for mask"
    )
    position_relative_to_layer = t.Bool(
        False,
        help="position relative to layer"
    )
    layer_mask_disabled = t.Bool(
        False,
        help="Layer mask disabled"
    )
    invert_layer_mask_when_blending = t.Bool(
        False,
        help="Invert layer mask when blending (obsolete)"
    )
    user_mask_from_rendering_other_data = t.Bool(
        False,
        help="Indicates that the user mask actually came from rendering other "
             "data"
    )
    user_mask_density = t.Int(
        None, min=0, max=255, allow_none=True,
        help="User mask density"
    )
    user_mask_feather = t.Float(
        None, allow_none=True,
        help="User mask feather"
    )
    vector_mask_density = t.Int(
        None, min=0, max=255, allow_none=True,
        help="Vector mask density"
    )
    vector_mask_feather = t.Float(
        None, allow_none=True,
        help="Vector mask feather"
    )
    real_flags = t.Int()
    real_background_color = t.Bool()
    real_top = t.Int()
    real_left = t.Int()
    real_bottom = t.Int()
    real_right = t.Int()

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

    def length(self, header, is_set_to_default=None):
        if is_set_to_default is None:
            is_set_to_default = util.is_set_to_default(self)
        if is_set_to_default:
            return 0
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
    def read(cls, fd, header):
        length = util.read_value(fd, 'I')
        d = {}
        end = fd.tell() + length
        util.log("length: {}, end: {}", length, end)

        if length == 0:
            return cls(**d)

        top, left, bottom, right = struct.unpack('>iiii', fd.read(16))
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

        top, left, bottom, right = struct.unpack('>iiii', fd.read(16))
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
            fd.write(
                struct.pack(
                    '>iiii', top, left, bottom, right))

        def write_default_color(color):
            if color:
                util.write_value(fd, 'B', 255)
            else:
                util.write_value(fd, 'B', 0)

        is_set_to_default = util.is_set_to_default(self)

        util.write_value(fd, 'I', self.length(header, is_set_to_default))
        if is_set_to_default:
            return

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
        write_default_color(self.real_background_color)
        write_rectangle(self.real_top, self.real_left,
                        self.real_bottom, self.real_right)
    write.__doc__ = docs.write


class ChannelImageData(t.HasTraits):
    """
    A single plane of channel image data.
    """
    compression = t.Enum(
        list(enums.Compression),
        default_value=enums.Compression.rle,
        help="Compression method. See `enums.Compression`."
    )

    def __init__(self, image=None, fd=None, offset=None, size=None,
                 shape=None, depth=None, version=None,
                 compression=enums.Compression.raw):
        t.HasTraits.__init__(self, compression=compression)
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
            tell = self._fd.tell()
            try:
                self._fd.seek(self._offset)
                data = self._fd.read(self._size)
            finally:
                self._fd.seek(tell)
            fd.write(data)
        return fd.tell() - start
    write.__doc__ = docs.write


class LayerRecord(t.HasTraits):
    """
    Layer record.

    There is one of these per logical layer in the file.
    """
    top = t.Int(
        help="Top of the rectangle containing the layer."
    )
    left = t.Int(
        help="Left of the rectangle containing the layer."
    )
    bottom = t.Int(
        help="Bottom of the rectangle containing the layer."
    )
    right = t.Int(
        help="Right of the rectangle containing the layer."
    )
    blend_mode = t.Enum(
        list(enums.BlendMode), default_value=enums.BlendMode.normal,
        help="Blend mode. See `enums.BlendMode`"
    )
    opacity = t.Int(
        255, min=0, max=255,
        help="Opacity. 0=transparent, 255=opaque"
    )
    clipping = t.Bool(
        False,
        help="Clipping. False=base, True=non-base"
    )
    transparency_protected = t.Bool(
        False,
        help="Transparency protected"
    )
    visible = t.Bool(
        True,
        help="Visible"
    )
    pixel_data_irrelevant = t.Bool(
        False,
        help="Pixel data is irrelevant to appearance of document"
    )
    mask = t.Instance(
        LayerMask,
        help="`LayerMask`"
    )
    blending_ranges = t.Instance(
        blending_range.BlendingRanges,
        help='`blending_range.BlendingRanges`'
    )
    name = t.Unicode(
        min=0, max=255, default_value='',
        help="Name of layer"
    )
    channels = t.Dict(
        help="Dictionary from `enums.ChannelId` to `ChannelImageData`."
    )
    blocks = t.List(
        t.Instance(tagged_block.TaggedBlock),
        help="List of `tagged_block.TaggedBlock` items with additional "
             "information about this layer."
    )

    @t.default('mask')
    def _default_mask(self):
        return LayerMask()

    @t.default('blending_ranges')
    def _default_blending_ranges(self):
        return blending_range.BlendingRanges()

    @t.validate('channels')
    def _validate_channels(self, proposal):
        value = proposal['value']

        for key, val in value.items():
            try:
                enums.ChannelId(key)
            except ValueError as e:
                raise t.TraitError(str(e))

            if not isinstance(val, ChannelImageData):
                raise t.TraitError(
                    "Each channel must be ChannelImageData instance")

        value = collections.OrderedDict(
            sorted([(k, v) for (k, v) in value.items()]))

        return value

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
        top, left, bottom, right = struct.unpack('>iiii', fd.read(16))

        util.log("position: ({}, {}, {}, {})", top, left, bottom, right)

        num_channels = util.read_value(fd, 'H')
        channel_ids = []
        channel_data_lengths = []
        for i in range(num_channels):
            channel_ids.append(util.read_value(fd, 'h'))
            if header.version == 1:
                channel_data_lengths.append(util.read_value(fd, 'I'))
            else:
                channel_data_lengths.append(util.read_value(fd, 'Q'))

        util.log(
            "num_channels: {}, channel_ids: {}, channel_data_lengths: {}",
            num_channels, channel_ids, channel_data_lengths
        )

        blend_mode_signature = fd.read(4)
        if blend_mode_signature != b'8BIM':
            raise ValueError(
                "Invalid blend mode signature '{}'".format(
                    blend_mode_signature))

        blend_mode = fd.read(4)
        opacity = util.read_value(fd, 'B')
        clipping = bool(util.read_value(fd, 'B'))
        flags = util.read_value(fd, 'B')
        (transparency_protected,
         visible,
         _,
         _,
         pixel_data_irrelevant) = util.unpack_bitflags(flags, 5)
        visible = not visible
        fd.seek(1, 1)  # filler

        util.log(
            "blend_mode: {}, opacity: {}, clipping: {}, flags: {}",
            blend_mode, opacity, clipping, flags
        )

        extra_length = util.read_value(fd, 'I')
        end = fd.tell() + extra_length

        util.log("extra_length: {}, end: {}", extra_length, end)

        mask = LayerMask.read(fd, header)
        blending_ranges = blending_range.BlendingRanges.read(
            fd, header, num_channels)
        name = util.read_pascal_string(fd, 4)

        util.log("name: '{}'", name)

        blocks = []
        while fd.tell() < end:
            blocks.append(
                tagged_block.TaggedBlock.read(fd, header))
        fd.seek(end)

        result = cls(
            header,
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
            mask=mask,
            blending_ranges=blending_ranges,
            name=name,
            blocks=blocks
        )

        result._channel_data_lengths = channel_data_lengths
        result._channel_ids = channel_ids
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
        self.channels = channels

    @util.trace_write
    def write(self, fd, header):
        fd.write(struct.pack('>iiii',
                 self.top, self.left, self.bottom, self.right))
        util.write_value(fd, 'H', len(self.channels))
        self.channel_lengths_offset = fd.tell()
        if header.version == 1:
            fd.seek(6 * len(self.channels), 1)
        else:
            fd.seek(10 * len(self.channels), 1)
        fd.write(b'8BIM')
        fd.write(self.blend_mode)
        util.write_value(fd, 'B', self.opacity)
        util.write_value(fd, 'B', int(self.clipping))
        flags = util.pack_bitflags(
            self.transparency_protected,
            not self.visible,
            False,
            True,
            self.pixel_data_irrelevant)
        util.write_value(fd, 'B', flags)
        fd.write(b'\0')  # filler

        extra_length = (
            self.mask.total_length(header) +
            self.blending_ranges.total_length(header) +
            util.pascal_string_length(self.name, 4) +
            sum(x.total_length(header) for x in self.blocks)
        )
        util.write_value(fd, 'I', extra_length)
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
        for channel_id, length in zip(self.channels.keys(), lengths):
            util.write_value(fd, 'h', channel_id)
            if header.version == 1:
                util.write_value(fd, 'I', length)
            else:
                util.write_value(fd, 'Q', length)
        fd.seek(offset)


class LayerInfo(t.HasTraits):
    """
    A set of `LayerRecord` instances.
    """
    layer_records = t.List(
        t.Instance(LayerRecord),
        help="List of `LayerRecord` instances"
    )
    use_alpha_channel = t.Bool(
        False,
        help="Indicates that the first channel contains transparency data for "
             "the merged result."
    )

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


class GlobalLayerMaskInfo(t.HasTraits):
    """
    Global layer mask info.
    """
    overlay_color_space = t.Bytes(
        b'\0' * 10, min=10, max=10,
        help="Undocumented"
    )
    opacity = t.Int(
        100, min=0, max=100,
        help="Opacity. 0=transparent, 100=opaque"
    )
    kind = t.Enum(
        list(enums.LayerMaskKind),
        default_value=enums.LayerMaskKind.use_value_stored_per_layer,
        help="Layer mask kind. See `enums.LayerMaskKind`"
    )

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        length = util.read_value(fd, 'I')
        end = fd.tell() + length
        util.log("length: {}, end: {}", length, end)
        if length == 0:
            return cls()

        overlay_color_space = fd.read(10)
        opacity = util.read_value(fd, 'H')
        kind = util.read_value(fd, 'B')

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
        if util.is_set_to_default(self):
            util.write_value(fd, 'I', 0)
        else:
            util.write_value(fd, 'I', 16)
            fd.write(self.overlay_color_space)
            util.write_value(fd, 'H', self.opacity)
            util.write_value(fd, 'B', self.kind)
            fd.write(b'\0\0\0')  # filler
    write.__doc__ = docs.write


class LayerAndMaskInfo(t.HasTraits):
    """
    Layer and mask information section.
    """
    layer_info = t.Instance(
        LayerInfo,
        help="Layer info. See `LayerInfo`."
    )
    global_layer_mask_info = t.Instance(
        GlobalLayerMaskInfo, allow_none=True,
        help="Global layer mask info. See `GlobalLayerMaskInfo`."
    )
    additional_layer_info = t.List(
        t.Instance(tagged_block.TaggedBlock),
        help="List of additional layer info. See `TaggedBlock`."
    )

    @t.default('layer_info')
    def _default_layer_info(self):
        return LayerInfo()

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
