# -*- coding: utf-8 -*-


import struct


import traitlets as t


from . import enums
from . import util


class LayerMask(t.HasTraits):
    top = t.Int()
    left = t.Int()
    bottom = t.Int()
    right = t.Int()
    default_color = t.Bool(False)
    position_relative_to_layer = t.Bool(False)
    layer_mask_disabled = t.Bool(False)
    invert_layer_mask_when_blending = t.Bool(False)
    user_mask_from_rendering_other_data = t.Bool(False)
    user_mask_density = t.Int(None, min=0, max=255, allow_none=True)
    user_mask_feather = t.Float(None, allow_none=True)
    vector_mask_density = t.Int(None, min=0, max=255, allow_none=True)
    vector_mask_feather = t.Float(None, allow_none=True)
    real_flags = t.Int()
    real_background_color = t.Bool()
    real_top = t.Int()
    real_left = t.Int()
    real_bottom = t.Int()
    real_right = t.Int()

    def length(self, header):
        if util.is_set_to_default(self):
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

    def total_length(self, header):
        return 4 + self.length(header)

    def _get_mask_flags(self):
        mask_flags = 0
        if self.user_mask_density is not None:
            mask_flags |= 1
        if self.user_mask_feather is not None:
            mask_flags |= 2
        if self.vector_mask_density is not None:
            mask_flags |= 4
        if self.vector_mask_feather is not None:
            mask_flags |= 8
        return mask_flags

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
        d['position_relative_to_layer'] = bool(flags & 1)
        d['layer_mask_disabled'] = bool(flags & 2)
        d['invert_layer_mask_when_blending'] = bool(flags & 4)
        d['user_mask_from_rendering_other_data'] = bool(flags & 8)

        util.log("default_color: {}, flags: {}", d['default_color'], flags)

        if length == 20:
            util.log("done early")
            fd.seek(end)
            return cls(**d)

        if flags & 16:
            mask_parameters = util.read_value(fd, 'B')
            if mask_parameters & 1:
                d['user_mask_density'] = util.read_value(fd, 'B')
            if mask_parameters & 2:
                d['user_mask_feather'] = util.read_value(fd, 'd')
            if mask_parameters & 4:
                d['vector_mask_density'] = util.read_value(fd, 'B')
            if mask_parameters & 8:
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

        util.write_value(fd, 'I', self.length(header))
        if util.is_set_to_default(self):
            return

        write_rectangle(self.top, self.left, self.bottom, self.right)
        write_default_color(self.default_color)

        flags = 0
        if self.position_relative_to_layer:
            flags |= 1
        if self.layer_mask_disabled:
            flags |= 2
        if self.invert_layer_mask_when_blending:
            flags |= 4
        if self.user_mask_from_rendering_other_data:
            flags |= 7
        mask_flags = self._get_mask_flags()
        if mask_flags:
            flags |= 16

        util.write_value(fd, 'B', flags)

        if mask_flags:
            util.write_value(fd, 'B', mask_flags)

            if self.user_mask_density:
                util.write_value(fd, 'B', self.user_mask_density)
            if self.user_mask_feather:
                util.write_value(fd, 'd', self.user_make_feather)
            if self.vector_mask_density:
                util.write_value(fd, 'B', self.vector_mask_density)
            if self.vector_mask_feather:
                util.write_value(fd, 'd', self.vector_mask_feather)

        util.write_value(fd, 'B', self.real_flags)
        write_default_color(self.real_background_color)
        write_rectangle(self.real_top, self.real_left,
                        self.real_bottom, self.real_right)


class BlendingRange(t.HasTraits):
    black0 = t.Int(min=0, max=255)
    black1 = t.Int(min=0, max=255)
    white0 = t.Int(min=0, max=255)
    white1 = t.Int(min=0, max=255)

    def length(self, header):
        return 4

    total_length = length

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        black0, black1, white0, white1 = struct.unpack('>BBBB', fd.read(4))

        util.log(
            "black: ({}, {}), white: ({}, {})",
            black0, black1, white0, white1)

        return cls(
            black0=black0,
            black1=black1,
            white0=white0,
            white1=white1)

    @util.trace_write
    def write(self, fd, header):
        fd.write(struct.pack(
            '>BBBB', self.black0, self.black1, self.white0, self.white1))


class BlendingRangePair(t.HasTraits):
    src = t.Instance(BlendingRange)
    dst = t.Instance(BlendingRange)

    def length(self, header):
        return 8

    total_length = length

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        src = BlendingRange.read(fd, header)
        dst = BlendingRange.read(fd, header)

        return cls(src=src,
                   dst=dst)

    @util.trace_write
    def write(self, fd, header):
        self.src.write(fd, header)
        self.dst.write(fd, header)


class BlendingRanges(t.HasTraits):
    composite_gray_blend = t.Instance(BlendingRangePair, allow_none=True)
    channels = t.List(t.Instance(BlendingRangePair))

    def length(self, header):
        if self.composite_gray_blend is not None:
            return (
                self.composite_gray_blend.total_length(header) +
                sum(x.total_length(header) for x in self.channels))
        return 0

    def total_length(self, header):
        return 4 + self.length(header)

    @classmethod
    @util.trace_read
    def read(cls, fd, header, num_channels):
        length = util.read_value(fd, 'I')
        end = fd.tell() + length
        util.log("length: {}, end: {}", length, end)
        if length == 0:
            return cls()

        composite_gray_blend = BlendingRangePair.read(fd, header)
        channels = []
        while fd.tell() < end:
            channels.append(BlendingRangePair.read(fd, header))

        fd.seek(end)

        return cls(
            composite_gray_blend=composite_gray_blend,
            channels=channels)

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'I', self.length(header))
        if self.composite_gray_blend is not None:
            self.composite_gray_blend.write(fd, header)
            for channel in self.channels:
                channel.write(fd, header)


class ChannelImageData(util.DeferredLoad, t.HasTraits):
    def __init__(self, data, **kwargs):
        util.DeferredLoad.__init__(self, data)
        t.HasTraits.__init__(self, **kwargs)

    compression = t.Enum(list(enums.Compression))

    def length(self, header):
        return self.data_length

    def total_length(self, header):
        return 2 + self.length(header)

    @classmethod
    @util.trace_read
    def read(cls, fd, header, size):
        compression = util.read_value(fd, 'H')
        util.log("compression: {}", enums.Compression(compression))
        data = (fd, fd.tell(), size)
        fd.seek(size, 1)
        return cls(data, compression=compression)

    @util.trace_write
    def write(self, fd, header):
        util.write_value(fd, 'H', self.compression)
        fd.write(self.data)


class TaggedBlock(t.HasTraits):
    code = t.Bytes(min=4, max=4)
    data = t.Bytes()

    _large_layer_info_codes = set([
        b'LMsk', b'Lr16', b'Lr32', b'Layr', b'Mt16', b'Mt32',
        b'Mtrn', b'Alph', b'FMsk', b'Ink2', b'FEid', b'FXid',
        b'PxSD'])

    def length(self, header):
        return len(self.data)

    def total_length(self, header, padding=1):
        length = 8
        if header.version == 2 and self.code in self._large_layer_info_codes:
            length += 8
        else:
            length += 4
        length += util.pad(len(self.data), padding)
        return length

    @classmethod
    @util.trace_read
    def read(cls, fd, header, padding=1):
        signature = fd.read(4)
        if signature not in (b'8BIM', b'8B64'):
            raise ValueError('Invalid signature in tagged block')

        code = fd.read(4)

        if header.version == 2 and code in cls._large_layer_info_codes:
            length = util.read_value(fd, 'Q')
        else:
            length = util.read_value(fd, 'I')
        padded_length = util.pad(length, padding)

        util.log(
            "code: {}, length: {}, padded_length: {}",
            code, length, padded_length
        )

        data = fd.read(length)
        fd.seek(padded_length - length, 1)

        return cls(code=code, data=data)

    @util.trace_write
    def write(self, fd, header, padding=1):
        if header.version == 2 and self.code in self._large_layer_info_codes:
            fd.write(b'8B64')
        else:
            fd.write(b'8BIM')
        fd.write(self.code)
        length = len(self.data)
        padded_length = util.pad(length, padding)
        if header.version == 2 and self.code in self._large_layer_info_codes:
            util.write_value(fd, 'Q', length)
        else:
            util.write_value(fd, 'I', length)
        fd.write(self.data)
        fd.write(b'\0' * (padded_length - length))


class LayerRecord(t.HasTraits):
    top = t.Int()
    left = t.Int()
    bottom = t.Int()
    right = t.Int()
    channel_ids = t.List(t.Int())
    blend_mode_key = t.Enum(list(enums.BlendModeKey))
    opacity = t.Int(min=0, max=255)
    clipping = t.Bool()
    transparency_protected = t.Bool()
    visible = t.Bool()
    pixel_data_irrelevant = t.Bool()
    mask = t.Instance(LayerMask, allow_none=True)
    blending_ranges = t.Instance(BlendingRanges, allow_none=True)
    name = t.Unicode(min=0, max=255, allow_none=True)
    channel_data = t.List(t.Instance(ChannelImageData))
    blocks = t.List(t.Instance(TaggedBlock))

    def length(self, header):
        length = 16 + 2
        if header.version == 1:
            length += len(self.channel_ids) * 6
        else:
            length += len(self.channel_ids) * 10
        length += 4 + 4 + 1 + 1 + 1 + 1 + 4
        if self.mask is not None:
            length += self.mask.total_length(header)
        if self.blending_ranges is not None:
            length += self.blending_ranges.total_length(header)
        if self.name is not None:
            length += util.pascal_string_length(self.name, 4)
        for block in self.blocks:
            length += block.total_length(header)
        return length

    total_length = length

    def total_data_length(self, header):
        return sum(x.total_length(header) for x in self.channel_data)

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

        blend_mode_key = fd.read(4)
        opacity = util.read_value(fd, 'B')
        clipping = bool(util.read_value(fd, 'B'))
        flags = util.read_value(fd, 'B')
        transparency_protected = bool(flags & 1)
        visible = bool(flags & 2)
        pixel_data_irrelevant = bool(flags & 16)
        fd.seek(1, 1)  # filler

        util.log(
            "blend_mode_key: {}, opacity: {}, clipping: {}, flags: {}",
            blend_mode_key, opacity, clipping, flags
        )

        extra_length = util.read_value(fd, 'I')
        end = fd.tell() + extra_length

        util.log("extra_length: {}, end: {}", extra_length, end)

        mask = LayerMask.read(fd, header)
        blending_ranges = BlendingRanges.read(fd, header, num_channels)
        name = util.read_pascal_string(fd, 4)

        util.log("name: '{}'", name)

        blocks = []
        while fd.tell() < end:
            blocks.append(
                TaggedBlock.read(fd, header))
        fd.seek(end)

        result = cls(
            top=top,
            left=left,
            bottom=bottom,
            right=right,
            channel_ids=channel_ids,
            blend_mode_key=blend_mode_key,
            opacity=opacity,
            clipping=clipping,
            transparency_protected=transparency_protected,
            visible=visible,
            pixel_data_irrelevant=pixel_data_irrelevant,
            mask=mask,
            blending_ranges=blending_ranges,
            name=name,
            blocks=blocks)

        result._channel_data_lengths = channel_data_lengths
        return result

    def read_channel_data(self, fd, header):
        for channel_length in self._channel_data_lengths:
            self.channel_data.append(
                ChannelImageData.read(fd, header, channel_length - 2))

    @util.trace_write
    def write(self, fd, header):
        if len(self.channel_ids) != len(self.channel_data):
            raise ValueError(
                "Mismatched number of channel ids ({}) "
                "and channel data ({})".format(
                    len(self.channel_ids), len(self.channel_data)))

        fd.write(struct.pack('>iiii',
                 self.top, self.left, self.bottom, self.right))
        util.write_value(fd, 'H', len(self.channel_ids))
        for channel_id, image in zip(self.channel_ids, self.channel_data):
            util.write_value(fd, 'h', channel_id)
            util.write_value(fd, 'I', image.total_length(header))
        fd.write(b'8BIM')
        fd.write(self.blend_mode_key)
        util.write_value(fd, 'B', self.opacity)
        util.write_value(fd, 'B', int(self.clipping))
        flags = 8
        if self.transparency_protected:
            flags |= 1
        if self.visible:
            flags |= 2
        if self.pixel_data_irrelevant:
            flags |= 16
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

    def write_channel_data(self, fd, header):
        for data in self.channel_data:
            data.write(fd, header)


class LayerInfo(t.HasTraits):
    layers = t.List(t.Instance(LayerRecord))
    use_alpha_channel = t.Bool()

    def length(self, header):
        if len(self.layers):
            return util.round_up(
                2 +
                sum(x.total_length(header) for x in self.layers) +
                sum(x.total_data_length(header) for x in self.layers))
        else:
            return 0

    def total_length(self, header):
        if header.version == 1:
            return 4 + self.length(header)
        else:
            return 8 + self.length(header)

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

            layers = [
                LayerRecord.read(fd, header) for i in range(layer_count)]
            for layer in layers:
                layer.read_channel_data(fd, header)

            fd.seek(end)

            return cls(layers=layers,
                       use_alpha_channel=use_alpha_channel)
        else:
            return cls()

    @util.trace_write
    @util.pad_block
    def write(self, fd, header):
        if header.version == 1:
            util.write_value(fd, 'I', self.length(header))
        else:
            util.write_value(fd, 'Q', self.length(header))
        layer_count = len(self.layers)
        if layer_count == 0:
            return
        if self.use_alpha_channel:
            layer_count *= -1
        util.write_value(fd, 'h', layer_count)
        for layer in self.layers:
            layer.write(fd, header)
        for layer in self.layers:
            layer.write_channel_data(fd, header)


class GlobalLayerMaskInfo(t.HasTraits):
    overlay_color_space = t.Bytes(b'\0' * 10, min=10, max=10)
    opacity = t.Int(100, min=0, max=100)
    kind = t.Int(min=0, max=255)

    def length(self, header):
        if util.is_set_to_default(self):
            return 0
        else:
            return 16

    def total_length(self, header):
        return 4 + self.length(header)

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


class LayerAndMaskInfo(t.HasTraits):
    layer_info = t.Instance(LayerInfo)
    global_layer_mask_info = t.Instance(GlobalLayerMaskInfo)
    additional_layer_info = t.List(t.Instance(TaggedBlock))

    def length(self, header):
        return (
            self.layer_info.total_length(header) +
            self.global_layer_mask_info.total_length(header) +
            sum(x.total_length(header, 4) for x in self.additional_layer_info))

    def total_length(self, header):
        if header.version == 1:
            return 4 + self.length(header)
        else:
            return 8 + self.length(header)

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

        global_layer_mask_info = GlobalLayerMaskInfo()
        additional_layer_info = []
        if fd.tell() < end:
            global_layer_mask_info = GlobalLayerMaskInfo.read(fd, header)

            while fd.tell() < end:
                additional_layer_info.append(
                    TaggedBlock.read(fd, header, 4))

        return cls(layer_info=layer_info,
                   global_layer_mask_info=global_layer_mask_info,
                   additional_layer_info=additional_layer_info)

    @util.trace_write
    def write(self, fd, header):
        if header.version == 1:
            util.write_value(fd, 'I', self.length(header))
        else:
            util.write_value(fd, 'Q', self.length(header))

        self.layer_info.write(fd, header)
        self.global_layer_mask_info.write(fd, header)
        for layer_info in self.additional_layer_info:
            layer_info.write(fd, header, 4)
