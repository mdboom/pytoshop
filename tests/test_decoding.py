# -*- coding: utf-8 -*-


import numpy as np
from numpy.testing import assert_array_equal
import pytest


from psdwriter import decoding
from psdwriter import enums


@pytest.mark.parametrize("depth", (8, 16))
def test_zip_with_prediction(depth):
    np.random.seed(0)

    dtype = decoding.color_depth_dtype_map[depth]
    x = np.random.randint(0, (2**depth) - 1, size=(256, 256), dtype=dtype)

    data = decoding.compress_image(
        x, enums.Compression.zip_prediction, depth, 1)
    y = decoding.decompress_image(
        data, enums.Compression.zip_prediction, (256, 256), depth, 1)

    assert_array_equal(x, y)


@pytest.mark.parametrize("depth", (1, 8, 16, 32))
def test_zip(depth):
    np.random.seed(0)

    dtype = decoding.color_depth_dtype_map[depth]
    x = np.random.randint(0, (2**depth) - 1, size=(256, 256), dtype=dtype)

    data = decoding.compress_image(
        x, enums.Compression.zip, depth, 1)
    y = decoding.decompress_image(
        data, enums.Compression.zip, (256, 256), depth, 1)

    assert_array_equal(x, y)


@pytest.mark.parametrize("depth", (1, 8, 16, 32))
@pytest.mark.parametrize("version", (1, 2))
def test_rle(depth, version):
    np.random.seed(0)

    dtype = decoding.color_depth_dtype_map[depth]
    x = np.random.randint(0, (2**depth) - 1, size=(256, 256), dtype=dtype)

    data = decoding.compress_image(
        x, enums.Compression.rle, depth, version)
    y = decoding.decompress_image(
        data, enums.Compression.rle, (256, 256), depth, version)

    assert_array_equal(x, y)
