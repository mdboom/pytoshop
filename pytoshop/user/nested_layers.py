# -*- coding: utf-8 -*-


"""
Convert a PSD file to/from nested layers.
"""


from collections import OrderedDict
import sys


import numpy as np
import six


from .. import core
from .. import enums
from .. import image_resources
from .. import layers as mlayers
from .. import path
from .. import tagged_block
from .. import util


class Layer(object):
    """
    Base class of all layers.
    """
    @property
    def name(self):
        "The name of the layer"
        return self._name

    @name.setter
    def name(self, value):
        if isinstance(value, bytes):
            value = value.decode('ascii')

        if not isinstance(value, six.text_type):
            raise TypeError("name must be a Unicode string")
        self._name = value

    @property
    def visible(self):
        "Is layer visible?"
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = bool(value)

    @property
    def opacity(self):
        "Opacity. 0=transparent, 255=opaque"
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > 255):
            raise ValueError(
                "opacity must be an integer in the range 0 to 255"
            )
        self._opacity = value

    @property
    def group_id(self):
        "Linked layer id"
        return self._group_id

    @group_id.setter
    def group_id(self, value):
        if (not isinstance(value, int) or
                value < 0 or value > ((1 << 16) - 1)):
            raise ValueError(
                "group_id must be a 16-bit unsigned int"
            )
        self._group_id = value

    @property
    def blend_mode(self):
        "blend mode"
        return self._blend_mode

    @blend_mode.setter
    def blend_mode(self, value):
        if value not in list(enums.BlendMode):
            raise ValueError("Invalid blend mode")
        self._blend_mode = value

    @property
    def metadata(self):
        "metadata"
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        if not isinstance(value, dict):
            raise TypeError("metadata must be a dict from bytes to bytes")
        for k, v in value.items():
            if not isinstance(k, bytes) or not isinstance(v, bytes):
                raise TypeError("metadata must be a dict from bytes to bytes")
        self._metadata = value


class Group(Layer):
    """
    A `Layer` that may contain other `Layer` instances.
    """
    def __init__(self,
                 name='',
                 visible=True,
                 opacity=255,
                 group_id=0,
                 blend_mode=enums.BlendMode.pass_through,
                 layers=None,
                 closed=True,
                 metadata=None):
        self.name = name
        self.visible = visible
        self.opacity = opacity
        self.group_id = group_id
        self.blend_mode = blend_mode
        if layers is None:
            layers = []
        self.layers = layers
        self.closed = closed
        if metadata is None:
            metadata = {}
        self.metadata = metadata

    @property
    def layers(self):
        "List of sublayers"
        return self._layers

    @layers.setter
    def layers(self, value):
        util.assert_is_list_of(value, Layer)
        self._layers = value

    @property
    def closed(self):
        "Is layer closed in GUI?"
        return self._closed

    @closed.setter
    def closed(self, value):
        self._closed = bool(value)


class Image(Layer):
    """
    A `Layer` containing image data, i.e. a leaf node.
    """
    def __init__(self,
                 name='',
                 visible=True,
                 opacity=255,
                 group_id=0,
                 blend_mode=enums.BlendMode.normal,
                 top=0, left=0, bottom=None, right=None,
                 channels={},
                 metadata=None):
        self.name = name
        self.visible = visible
        self.opacity = opacity
        self.group_id = group_id
        self.blend_mode = blend_mode
        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right
        self.channels = channels
        if metadata is None:
            metadata = {}
        self.metadata = metadata

    @property
    def top(self):
        "The top of the layer, in pixels."
        return self._top

    @top.setter
    def top(self, value):
        if not isinstance(value, int):
            raise TypeError("top must be an int")
        self._top = value

    @property
    def left(self):
        "The left of the layer, in pixels."
        return self._left

    @left.setter
    def left(self, value):
        if not isinstance(value, int):
            raise TypeError("left must be an int")
        self._left = value

    @property
    def bottom(self):
        """
        The bottom of the layer, in pixels. If not provided, will be
        automatically determined from channel data.
        """
        return self._bottom

    @bottom.setter
    def bottom(self, value):
        if value is not None and not isinstance(value, int):
            raise TypeError("bottom must be an int or None")
        self._bottom = value

    @property
    def right(self):
        """
        The right of the layer, in pixels. If not provided, will be
        automatically determined from channel data.
        """
        return self._right

    @right.setter
    def right(self, value):
        if value is not None and not isinstance(value, int):
            raise TypeError("right must be an int or None")
        self._right = value

    @property
    def channels(self):
        """
        The channel image data. May be one of the following:
        - A dictionary from `enums.ChannelId` to 2-D numpy arrays.
        - A 3-D numpy array of the shape (num_channels, height, width)
        - A list of numpy arrays where each is a channel.
        """
        return self._channels

    @channels.setter
    def channels(self, value):
        def coerce(value):
            if isinstance(value, dict):
                for key in value.keys():
                    enums.ChannelId(key)
                return value

            if isinstance(value, np.ndarray):
                if len(value.shape) == 3:
                    return dict((i, plane) for (i, plane) in enumerate(value))
                else:
                    return {0: value}

            if isinstance(value, list):
                return dict((i, plane) for (i, plane) in enumerate(value))

            return {0: value}

        self._channels = coerce(value)


def _iterate_all_images(layers):
    """
    Iterate over all `Image` instances in a hierarchy of `Layer`
    instances.
    """
    if isinstance(layers, list):
        for layer in layers:
            for sublayer in _iterate_all_images(layer):
                yield sublayer
    if isinstance(layers, Group):
        for sublayer in _iterate_all_images(layers.layers):
            yield sublayer
    elif isinstance(layers, Image):
        yield layers


def pprint_layers(layers, indent=0):
    """
    Pretty-print a hierarchy of `Layer` instances.
    """
    for layer in layers:
        if isinstance(layer, Group):
            print(('  ' * indent) + '< {}'.format(layer.name))
            pprint_layers(layer.layers, indent+1)
            print(('  ' * indent) + '>')
        elif isinstance(layer, Image):
            print(('  ' * indent) + '< {} ({}, {}, {}, {}) >'.format(
                layer.name, layer.top, layer.left, layer.bottom, layer.right))


def psd_to_nested_layers(psdfile):
    """
    Convert a `PsdFile` instance to a hierarchy of nested `Layer`
    instances.

    Parameters
    ----------
    psdfile : PsdFile
        A parsed PSD file.

    Returns
    -------
    layers : list of `Layer` instances
        A representation of the parsed hierarchy from the file.
    """
    if not isinstance(psdfile, core.PsdFile):
        raise TypeError("psdfile must be a pytoshop.core.PsdFile instance")

    group_ids_block = psdfile.image_resources.get_block(
        enums.ImageResourceID.layers_group_info)
    if group_ids_block is not None:
        group_ids = group_ids_block.group_ids
    else:
        group_ids = None

    layers = psdfile.layer_and_mask_info.layer_info.layer_records

    root = Group()
    group_stack = [root]

    for index, layer in reversed(list(enumerate(layers))):
        current_group = group_stack[-1]

        blocks = layer.blocks_map

        name = blocks.get(b'luni', layer).name
        divider = blocks.get(b'lsct', blocks.get(b'lsdk'))
        visible = layer.visible
        opacity = layer.opacity
        blend_mode = layer.blend_mode
        metadata = blocks.get(b'shmd', None)
        if metadata is None:
            metadata = {}
        else:
            metadata = metadata.datas
        extra_args = {}
        if group_ids is not None:
            extra_args['group_id'] = group_ids[index]

        if divider is not None:
            if divider.type in (enums.SectionDividerSetting.closed,
                                enums.SectionDividerSetting.open):
                # group begins
                group = Group(
                    name=name,
                    closed=(
                        divider.type == enums.SectionDividerSetting.closed),
                    blend_mode=blend_mode,
                    visible=visible,
                    opacity=opacity,
                    metadata=metadata,
                    **extra_args
                )
                group_stack.append(group)
                current_group.layers.append(group)

            elif divider.type == enums.SectionDividerSetting.bounding:
                # group ends
                if len(group_stack) == 1:
                    layers = group_stack[0].layers
                    layer = layers[0]

                    group = Group(
                        name=layer.name,
                        closed=False,
                        blend_mode=layer.blend_mode,
                        visible=layer.visible,
                        opacity=layer.opacity,
                        layers=layers[1:],
                        **extra_args
                    )

                    group_stack[0].layers = [group]

                else:
                    finished_group = group_stack.pop()
                    assert finished_group is not root

            else:
                raise ValueError("Invalid state")

        else:
            layer = Image(
                name=name,
                top=layer.top,
                left=layer.left,
                bottom=layer.bottom,
                right=layer.right,
                channels=layer.channels,
                blend_mode=blend_mode,
                visible=visible,
                opacity=opacity,
                metadata=metadata,
                **extra_args
            )
            current_group.layers.append(layer)

    return root.layers


def _flatten_group(layer, flat_layers, group_ids, compression, vector_mask):
    if layer.closed:
        divider_type = enums.SectionDividerSetting.closed
    else:
        divider_type = enums.SectionDividerSetting.open

    name_source = len(flat_layers)

    blocks = [
        tagged_block.UnicodeLayerName(name=layer.name),
        tagged_block.SectionDividerSetting(type=divider_type),
        tagged_block.LayerId(id=len(flat_layers))
    ]

    if len(layer.metadata):
        blocks.append(
            tagged_block.MetadataSetting(layer.metadata)
        )

    flat_layers.append(
        mlayers.LayerRecord(
            name=layer.name,
            blend_mode=layer.blend_mode,
            opacity=layer.opacity,
            visible=layer.visible,
            blocks=blocks,
            pixel_data_irrelevant=True
        )
    )

    group_ids.append(layer.group_id)

    _flatten_layers(
        layer.layers, flat_layers, group_ids, compression, vector_mask)

    flat_layers.append(
        mlayers.LayerRecord(
            blocks=[
                tagged_block.SectionDividerSetting(
                    type=enums.SectionDividerSetting.bounding),
                tagged_block.LayerNameSource(id=name_source)
            ],
            pixel_data_irrelevant=True
        )
    )

    group_ids.append(0)


def _flatten_image(layer, flat_layers, group_ids, compression, vector_mask):
    channels = OrderedDict()
    for id, im in layer.channels.items():
        if isinstance(im, mlayers.ChannelImageData):
            channels[id] = im
        else:
            channels[id] = mlayers.ChannelImageData(
                image=im, compression=compression)
    if (enums.ChannelId.transparency in channels and
            np.all(channels[enums.ChannelId.transparency].image == 0)):
        return

    blocks = [
        tagged_block.UnicodeLayerName(name=layer.name),
        tagged_block.LayerId(id=len(flat_layers))
    ]

    if vector_mask:
        blocks.append(
            tagged_block.VectorMask(
                path_resource=path.PathResource.from_rect(
                    layer.top + 5, layer.left + 5,
                    layer.bottom - 5, layer.right - 5
                )
            )
        )
    else:
        if enums.ChannelId.transparency not in channels:
            channels[enums.ChannelId.transparency] = \
                mlayers.ChannelImageData(
                    image=-1, compression=compression)

    if len(layer.metadata):
        blocks.append(
            tagged_block.MetadataSetting(layer.metadata)
        )

    flat_layers.append(
        mlayers.LayerRecord(
            top=layer.top,
            left=layer.left,
            bottom=layer.bottom,
            right=layer.right,
            name=layer.name,
            blend_mode=layer.blend_mode,
            opacity=layer.opacity,
            visible=layer.visible,
            channels=channels,
            blocks=blocks
        )
    )

    group_ids.append(layer.group_id)


def _flatten_layers(layers, flat_layers, group_ids, compression, vector_mask):
    for layer in layers:
        if isinstance(layer, Group):
            _flatten_group(
                layer, flat_layers, group_ids, compression, vector_mask
            )

        elif isinstance(layer, Image):
            _flatten_image(
                layer, flat_layers, group_ids, compression, vector_mask
            )

    return flat_layers, group_ids


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


def _determine_channels_and_depth(layers, depth):
    num_channels = 0
    for image in _iterate_all_images(layers):
        for index, channel in image.channels.items():
            if np.isscalar(channel):
                continue
            num_channels = max(num_channels, index + 1)
            channel_depth = channel.dtype.itemsize * 8
            if depth is None:
                depth = channel_depth
            elif depth != channel_depth:
                raise ValueError("Different image depths in input")

    if num_channels == 0 or depth is None:
        raise ValueError("Can't determine num channels or depth")

    return num_channels, depth


def _update_sizes(layers):
    for image in _iterate_all_images(layers):
        if len(image.channels) == 0:
            width = 0
            height = 0
        else:
            if image.bottom is not None and image.top is not None:
                height = image.bottom - image.top
            else:
                height = None
            if image.right is not None and image.left is not None:
                width = image.right - image.left
            else:
                width = None
            for index, channel in image.channels.items():
                if np.isscalar(channel) or channel.shape == ():
                    continue
                if height is None:
                    height = channel.shape[0]
                if width is None:
                    width = channel.shape[1]
                if (height, width) != channel.shape:
                    raise ValueError(
                        "Channels in image have different shapes or do not "
                        "match layer"
                    )
            if height is None or width is None:
                raise ValueError(
                    "Can't determine shape.  Set it explicitly."
                )

        if image.bottom is None:
            image.bottom = (image.top or 0) + height

        if image.right is None:
            image.right = (image.left or 0) + width


def nested_layers_to_psd(
        layers,
        color_mode,
        version=enums.Version.version_1,
        compression=enums.Compression.rle,
        depth=None,
        size=None,
        vector_mask=False):
    """
    Convert a hierarchy of nested `Layer` instances to a `PsdFile`.

    Parameters
    ----------
    layers : list of `Layer` instances
        The hierarchy of layers we want to create.

    color_mode : `enums.ColorMode`
        The color mode of the resulting PSD file (as well as the input
        image data).

    version : `enums.Version`, optional
        The version of the PSD spec to follow.

    compression : `enums.Compression`, optional
        The method of image compression to use for the layer image
        data.

    depth : `enums.ColorDepth`, optional
        The color depth of the resulting image.  Must match the color
        depth of the data passed in.  If not provided, the color depth
        will be automatically determined from the passed-in data.

    size : 2-tuple of int, optional
        The shape in the form ``(height, width)`` of the resulting PSD
        file.  If not provided, the height and width will be set to
        include all passed in layers, and the layers themselves will
        be adjusted so that none fall outside of the image.

    vector_mask : bool, optional
        When `True`, the mask for the layer will be a vector
        rectangle.  This results in much smaller file sizes, but is
        not quite as accurately rendered by Photoshop.  When `False`,
        a raster mask is used.

    Returns
    -------
    psdfile : PsdFile
        The resulting PSD file.
    """
    try:
        next(_iterate_all_images(layers))
    except StopIteration:
        raise ValueError("No images found in layers")

    _update_sizes(layers)

    num_channels, depth = _determine_channels_and_depth(layers, depth)

    if size is None:
        width, height = _adjust_positions(layers)
    else:
        width, height = size

    flat_layers, group_ids = _flatten_layers(
        layers, [], [], compression, vector_mask)

    flat_layers = flat_layers[::-1]
    group_ids = group_ids[::-1]

    f = core.PsdFile(
        version=version,
        num_channels=num_channels,
        height=height,
        width=width,
        depth=depth,
        color_mode=color_mode,
        layer_and_mask_info=mlayers.LayerAndMaskInfo(
            layer_info=mlayers.LayerInfo(
                layer_records=flat_layers
            )
        ),
        image_resources=image_resources.ImageResources(
            blocks=[
                image_resources.LayersGroupInfo(
                    group_ids=group_ids)
            ]
        ),
        compression=compression
    )

    return f
