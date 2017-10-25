# -*- coding: utf-8 -*-


import inspect
import io
import os


import numpy as np
import pytest


import pytoshop
from pytoshop import enums
from pytoshop import layers


DATA_PATH = os.path.join(os.path.dirname(__file__), 'psd_files')


def test_futz_with_channel_image_data():
    filename = os.path.join(DATA_PATH, 'group.psd')
    with open(filename, 'rb') as fd:
        psd = pytoshop.PsdFile.read(fd)

        first_layer = psd.layer_and_mask_info.layer_info.layer_records[0]

        first_layer.channels[0].image = np.empty((256, 256))
        with pytest.raises(ValueError):
            psd.write(io.BytesIO())

        first_layer.channels[0].image = np.empty((256,), np.uint8)
        with pytest.raises(ValueError):
            psd.write(io.BytesIO())

        first_layer.channels[0].image = np.empty((256, 256), np.uint8)
        with pytest.raises(ValueError):
            psd.write(io.BytesIO())

        first_layer.channels[0].image = 0
        psd.write(io.BytesIO())

        first_layer.channels[0].image = np.empty((200, 100), np.uint8)
        psd.write(io.BytesIO())


def test_futz_with_layer_channels():
    filename = os.path.join(DATA_PATH, 'group.psd')
    with open(filename, 'rb') as fd:
        psd = pytoshop.PsdFile.read(fd)

        first_layer = psd.layer_and_mask_info.layer_info.layer_records[0]

        with pytest.raises(TypeError):
            first_layer.channels = [
                layers.ChannelImageData(image=np.empty((200, 100), np.uint8))]

        first_layer.channels = {
            0: layers.ChannelImageData(image=np.empty((200, 100), np.uint8))}

        with pytest.raises(ValueError):
            channel = first_layer.get_channel(enums.ColorChannel.bitmap)

        first_layer.channels = {
            0:
            layers.ChannelImageData(image=np.empty((200, 100), np.uint8))}

        channel = first_layer.get_channel(enums.ColorChannel.red)
        assert channel.image.shape == (200, 100)

        first_layer.set_channel(
            enums.ColorChannel.green,
            first_layer.get_channel(enums.ColorChannel.red))

        first_layer.mask = first_layer.mask
        first_layer.blending_ranges = first_layer.blending_ranges

        psd.write(io.BytesIO())

        with pytest.raises(ValueError):
            first_layer.channels = {
                0: np.empty((200, 100), np.uint8)}

        with pytest.raises(ValueError):
            first_layer.channels = {
                'zero': layers.ChannelImageData(
                    image=np.empty((200, 100), np.uint8))}


def test_layer_mask_invalid_values():
    m = layers.LayerMask()

    for prop in ('top', 'left', 'right', 'bottom',
                 'real_top', 'real_left', 'real_right', 'real_bottom'):
        with pytest.raises(ValueError):
            setattr(m, prop, (1 << 32))

    for prop in ('user_mask_density', 'user_mask_feather',
                 'vector_mask_density', 'vector_mask_feather'):
        with pytest.raises(ValueError):
            setattr(m, prop, -1)

    with pytest.raises(TypeError):
        m.real_flags = None


def test_channel_image_data_invalid():
    args = inspect.getargspec(layers.ChannelImageData.__init__)
    for arg in args[0]:
        if arg in ('self', 'image', 'compression'):
            continue
        with pytest.raises(ValueError):
            layers.ChannelImageData(
                image=np.empty((0, 0), dtype='u8'),
                **{arg: 0})


def test_invalid_compression_type():
    with pytest.raises(ValueError):
        layers.ChannelImageData(compression=4)
    with pytest.raises(ValueError):
        layers.ChannelImageData(compression='zlib')


def test_layer_record_invalid_values():
    m = layers.LayerRecord()

    for prop in ('top', 'left', 'right', 'bottom'):
        with pytest.raises(ValueError):
            setattr(m, prop, (1 << 32))

    for prop in ('opacity', 'blend_mode'):
        with pytest.raises(ValueError):
            setattr(m, prop, -1)

    m.name = b'ascii'

    with pytest.raises(ValueError):
        m.name = u'X' * 256
