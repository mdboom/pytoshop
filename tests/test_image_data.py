# -*- coding: utf-8 -*-


import io


import numpy as np
import pytest


import pytoshop
from pytoshop import image_data


def test_image_data_invalid_shape():
    with pytest.raises(ValueError):
        image_data.ImageData(channels=np.empty((52,), dtype=np.uint16))


def test_image_data_invalid_dtype():
    with pytest.raises(ValueError):
        image_data.ImageData(channels=np.empty((52,)))


def test_image_valid_size():
    pytoshop.PsdFile(
        version=1,
        num_channels=3,
        height=256,
        width=256,
        depth=8,
        color_mode=3,
        image_data=image_data.ImageData(
            channels=np.empty((3, 256, 256), np.uint8)))


def test_image_invalid_size():
    psd = pytoshop.PsdFile(
        version=1,
        num_channels=3,
        height=256,
        width=256,
        depth=8,
        color_mode=3,
        image_data=image_data.ImageData(
            channels=np.empty((3, 254, 256), np.uint8)))

    with pytest.raises(ValueError):
        psd.write(io.BytesIO())
