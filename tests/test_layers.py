# -*- coding: utf-8 -*-


import io
import os


import numpy as np
import pytest


import pytoshop
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

        first_layer.channels = {
            0: layers.ChannelImageData(image=np.empty((200, 100), np.uint8))}
        psd.write(io.BytesIO())

        with pytest.raises(ValueError):
            first_layer.channels = {
                0: np.empty((200, 100), np.uint8)}

        with pytest.raises(ValueError):
            first_layer.channels = {
                'zero': layers.ChannelImageData(
                    image=np.empty((200, 100), np.uint8))}
