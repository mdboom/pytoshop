# -*- coding: utf-8 -*-


import io
import os


import numpy as np
import pytest


import pytoshop
from pytoshop import enums
from pytoshop.user import nested_layers


DATA_PATH = os.path.join(os.path.dirname(__file__), 'psd_files')


def test_nested_layers():
    filename = os.path.join(DATA_PATH, 'group.psd')
    with open(filename, 'rb') as fd:
        psd = pytoshop.PsdFile.read(fd)

        layers = nested_layers.psd_to_nested_layers(psd)

        nested_layers.pprint_layers(layers)

        psd2 = nested_layers.nested_layers_to_psd(layers, enums.ColorMode.rgb)

        fd = io.BytesIO()
        psd2.write(fd)


def test_nested_layers_no_adjust():
    filename = os.path.join(DATA_PATH, 'group.psd')
    with open(filename, 'rb') as fd:
        psd = pytoshop.PsdFile.read(fd)

        layers = nested_layers.psd_to_nested_layers(psd)

        psd2 = nested_layers.nested_layers_to_psd(
            layers, enums.ColorMode.rgb, size=(psd.width, psd.height))

        fd = io.BytesIO()
        psd2.write(fd)


def test_errors():
    with pytest.raises(TypeError):
        nested_layers.psd_to_nested_layers(None)


@pytest.mark.parametrize("vector_mask", (True, False))
def test_from_scratch(vector_mask):
    from pytoshop.user.nested_layers import Group, Image

    img1 = np.empty((100, 80), dtype=np.uint8)
    img2 = np.empty((100, 80), dtype=np.uint8)
    img3 = np.empty((100, 80), dtype=np.uint8)
    img4 = np.empty((2, 100, 80), dtype=np.uint8)

    layers = [
        Group(
            layers=[
                Image(channels={0: img1},
                      top=0, left=0, bottom=100, right=80),
                Image(channels=img2,
                      top=15, left=15),
                Image(channels=img4,
                      top=42, left=43),
                Image(channels=[img1, img1],
                      top=-5, left=49)
            ]),
        Image(channels={0: img3})
    ]

    psd = nested_layers.nested_layers_to_psd(
        layers, enums.ColorMode.grayscale,
        vector_mask=vector_mask)

    buff = io.BytesIO()
    psd.write(buff)

    buff.seek(0)

    pytoshop.read(buff)


def test_mixed_depth():
    from pytoshop.user.nested_layers import Group, Image

    img1 = np.empty((100, 80), dtype=np.uint8)
    img2 = np.empty((100, 80), dtype=np.uint16)

    layers = [
        Group(
            layers=[
                Image(channels={0: img1},
                      top=0, left=0, bottom=100, right=80),
                Image(channels=img2,
                      top=15, left=15),
            ])
    ]

    with pytest.raises(ValueError):
        nested_layers.nested_layers_to_psd(
            layers, enums.ColorMode.grayscale)


def test_mismatched_height():
    from pytoshop.user.nested_layers import Group, Image

    img1 = np.empty((100, 80), dtype=np.uint8)

    layers = [
        Group(
            layers=[
                Image(channels={0: img1},
                      top=0, left=0, bottom=101, right=80),
            ])
    ]

    with pytest.raises(ValueError):
        nested_layers.nested_layers_to_psd(
            layers, enums.ColorMode.grayscale)


def test_mismatched_width():
    from pytoshop.user.nested_layers import Group, Image

    img1 = np.empty((100, 80), dtype=np.uint8)

    layers = [
        Group(
            layers=[
                Image(channels={0: img1},
                      top=0, left=0, bottom=100, right=81),
            ])
    ]

    with pytest.raises(ValueError):
        nested_layers.nested_layers_to_psd(
            layers, enums.ColorMode.grayscale)


def test_mismatched_color_mode():
    from pytoshop.user.nested_layers import Group, Image

    img1 = np.empty((100, 80), dtype=np.uint8)

    im = Image(channels={0: img1},
               top=0, left=0, bottom=100, right=80,
               color_mode=enums.ColorMode.rgb)

    with pytest.raises(ValueError):
        im.get_channel(enums.ColorChannel.gray)
    im.get_channel(enums.ColorChannel.red)
    with pytest.raises(KeyError):
        im.get_channel(enums.ColorChannel.blue)

    layers = [
        Group(
            layers=[
                im
            ])
    ]

    with pytest.raises(ValueError):
        nested_layers.nested_layers_to_psd(
            layers, enums.ColorMode.grayscale)


def test_no_images():
    from pytoshop.user.nested_layers import Group

    layers = [
        Group(
            layers=[]
            )
        ]

    with pytest.raises(ValueError):
        nested_layers.nested_layers_to_psd(
            layers, enums.ColorMode.grayscale)


@pytest.mark.parametrize("compression", (0, 1, 2, 3))
def test_proxy(compression):
    from pytoshop.user.nested_layers import Group, Image

    class ImageProxy(object):
        @property
        def shape(self):
            return (1000, 1000)

        @property
        def dtype(self):
            return np.uint8().dtype

        def __array__(self):
            return np.arange(1000000, dtype=np.uint8).reshape((1000, 1000))

    image_layers = []
    for i in range(256):
        image_layers.append(
            Image(
                channels={0: ImageProxy()},
                top=i, left=i
            )
        )

    layers = [
        Group(
            layers=image_layers
        )
    ]

    psd = nested_layers.nested_layers_to_psd(
        layers, enums.ColorMode.grayscale,
        compression=compression
    )

    buff = io.BytesIO()
    psd.write(buff)

    buff.seek(0)

    psd = pytoshop.read(buff)
    layers = nested_layers.psd_to_nested_layers(psd)
    # Extract all the data so it's tested and included in the timings
    for image in layers[0].layers:
        [x.image for x in image.channels.values()]


def test_masked_layer():
    filename = os.path.join(DATA_PATH, 'masked_layer.psd')
    with open(filename, 'rb') as fd:
        psd = pytoshop.PsdFile.read(fd)

        layers = nested_layers.psd_to_nested_layers(psd)

        assert layers[0].channels[0].shape == layers[0].channels[-2].shape


if __name__ == '__main__':
    test_proxy(1)
