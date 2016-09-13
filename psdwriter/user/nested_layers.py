# -*- coding: utf-8 -*-


import sys


import traitlets as t


from .. import core
from .. import enums
from .. import layers as l
from .. import tagged_block


class Layer(t.HasTraits):
    name = t.Unicode()
    blend_mode = t.Enum(list(enums.BlendMode),
                        default_value=enums.BlendMode.normal)
    visible = t.Bool(default_value=True)
    opacity = t.Int(min=0, max=255)


class GroupLayer(Layer):
    layers = t.List(t.Instance(Layer))
    closed = t.Bool()


class ImageLayer(Layer):
    channels = t.Dict()
    top = t.Int()
    left = t.Int()
    bottom = t.Int()
    right = t.Int()


def _iterate_all_images(layers):
    if isinstance(layers, list):
        for layer in layers:
            yield from _iterate_all_images(layer)
    if isinstance(layers, GroupLayer):
        yield from _iterate_all_images(layers.layers)
    elif isinstance(layers, ImageLayer):
        yield layers


def pprint_layers(layers, indent=0):
    for layer in layers:
        if isinstance(layer, GroupLayer):
            print(('  ' * indent) + '< {}'.format(layer.name))
            pprint_layers(layer.layers, indent+1)
            print(('  ' * indent) + '>')
        elif isinstance(layer, ImageLayer):
            print(('  ' * indent) + '< {} ({}, {}, {}, {}) >'.format(
                layer.name, layer.top, layer.left, layer.bottom, layer.right))


def psd_to_nested_layers(psdfile):
    if not isinstance(psdfile, core.PsdFile):
        raise TypeError("psdfile must be a psdwriter.core.PsdFile instance")

    layers = psdfile.layer_and_mask_info.layer_info.layer_records

    root = GroupLayer()
    group_stack = [root]

    for index, layer in reversed(list(enumerate(layers))):
        current_group = group_stack[-1]

        blocks = layer.blocks_map

        name = blocks.get(b'luni', layer).name
        if b'lyid' in blocks:
            layer_id = blocks.get(b'lyid').id
        else:
            layer_id = None
        divider = blocks.get(b'lsct', blocks.get(b'lsdk'))
        visible = layer.visible
        opacity = layer.opacity
        blend_mode = layer.blend_mode

        if divider is not None:
            if divider.type in (enums.SectionDividerSetting.closed,
                                enums.SectionDividerSetting.open):
                # group begins
                group = GroupLayer(
                    name=name,
                    closed=(
                        divider.type == enums.SectionDividerSetting.closed),
                    blend_mode=blend_mode,
                    visible=visible,
                    opacity=opacity
                )
                group_stack.append(group)
                current_group.layers.append(group)

            elif divider.type == enums.SectionDividerSetting.bounding:
                # group ends
                if len(group_stack) == 1:
                    layers = group_stack[0].layers
                    layer = layers[0]

                    group = GroupLayer(
                        name=layer.name,
                        closed=False,
                        blend_mode=layer.blend_mode,
                        visible=layer.visible,
                        opacity=layer.opacity,
                        layers=layers[1:]
                    )

                    group_stack[0].layers = [group]

                else:
                    finished_group = group_stack.pop()
                    assert finished_group is not root

            else:
                raise ValueError("Invalid state")

        else:
            layer = ImageLayer(
                name=name,
                top=layer.top,
                left=layer.left,
                bottom=layer.bottom,
                right=layer.right,
                channels=dict(
                    (k, v.image) for (k, v) in layer.channels.items()),
                blend_mode=blend_mode,
                visible=visible,
                opacity=opacity
            )
            current_group.layers.append(layer)

    return root.layers


itemsize_to_depth = {
    1: 8,
    2: 16,
    4: 32
}


def _flatten_layers(layers, flat_layers, compression):
    for layer in layers:
        if isinstance(layer, GroupLayer):
            if layer.closed:
                divider_type = enums.SectionDividerSetting.closed
            else:
                divider_type = enums.SectionDividerSetting.open
            flat_layers.append(
                l.LayerRecord(
                    name=layer.name,
                    blend_mode=layer.blend_mode,
                    opacity=layer.opacity,
                    visible=layer.visible,
                    blocks=[
                        tagged_block.UnicodeLayerName(name=layer.name),
                        tagged_block.SectionDividerSetting(type=divider_type),
                        tagged_block.LayerId(id=len(flat_layers))
                    ]
                )
            )

            _flatten_layers(layer.layers, flat_layers, compression)

            flat_layers.append(
                l.LayerRecord(
                    blocks=[
                        tagged_block.SectionDividerSetting(
                            type=enums.SectionDividerSetting.bounding),
                        tagged_block.LayerNameSource(id=len(flat_layers))
                    ]
                )
            )

        elif isinstance(layer, ImageLayer):
            channels = dict(
                (id, l.ChannelImageData(image=im, compression=compression))
                for (id, im) in layer.channels.items())
            flat_layers.append(
                l.LayerRecord(
                    top=layer.top,
                    left=layer.left,
                    bottom=layer.bottom,
                    right=layer.right,
                    name=layer.name,
                    blend_mode=layer.blend_mode,
                    opacity=layer.opacity,
                    visible=layer.visible,
                    channels=channels,
                    blocks=[
                        tagged_block.UnicodeLayerName(name=layer.name),
                        tagged_block.LayerId(id=len(flat_layers))
                    ]
                )
            )

    return flat_layers


def _adjust_positions(layers):
    top = sys.maxsize
    left = sys.maxsize
    bottom = -sys.maxsize
    right = -sys.maxsize
    for image in _iterate_all_images(layers):
        top = min(image.top, top)
        left = min(image.left, left)
        bottom = max(image.bottom, bottom)
        right = max(image.right, right)

    yoffset = -top
    xoffset = -left

    for image in _iterate_all_images(layers):
        image.top += yoffset
        image.left += xoffset
        image.bottom += yoffset
        image.right += xoffset

    width = right - left
    height = bottom - top

    return width, height


def _determine_channels_and_depth(layers):
    num_channels = 0
    depth = None
    for image in _iterate_all_images(layers):
        for index, channel in image.channels.items():
            num_channels = max(num_channels, index + 1)
            channel_depth = channel.dtype.itemsize * 8
            if depth is None:
                depth = channel_depth
            elif depth != channel_depth:
                raise ValueError("Different image depths in input")

    return num_channels, depth


def nested_layers_to_psd(
        layers,
        version=enums.Version.version_1,
        compression=enums.Compression.zip,
        color_mode=enums.ColorMode.rgb,
        size=None):

    try:
        next(_iterate_all_images(layers))
    except StopIteration:
        raise ValueError("No images found in layers")

    num_channels, depth = _determine_channels_and_depth(layers)

    if size is None:
        width, height = _adjust_positions(layers)
    else:
        width, height = size

    flat_layers = _flatten_layers(layers, [], compression)[::-1]

    f = core.PsdFile(
        header=core.Header(
            version=version,
            num_channels=num_channels,
            height=height,
            width=width,
            depth=depth,
            color_mode=color_mode
        ),
        layer_and_mask_info=l.LayerAndMaskInfo(
            layer_info=l.LayerInfo(
                layer_records=flat_layers
            )
        )
    )

    return f
