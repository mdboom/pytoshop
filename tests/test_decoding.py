# -*- coding: utf-8 -*-


import numpy as np
from numpy.testing import assert_array_equal
import pytest


from psdwriter import decoding


@pytest.mark.parametrize("depth", (8, 16))
def test_zip_with_prediction(depth):
    np.random.seed(0)

    dtype = decoding.color_depth_dtype_map[depth]
    x = np.random.randint(0, (2**depth) - 1, size=(256, 256), dtype=dtype)
    x = x.astype(dtype)

    data = decoding.compress_zip_prediction(x, depth, 1)

    y = decoding.decompress_zip_prediction(data, (256, 256), depth, 1)

    assert_array_equal(x, y)


@pytest.mark.parametrize("depth", (1, 8, 16, 32))
def test_zip(depth):
    np.random.seed(0)

    dtype = decoding.color_depth_dtype_map[depth]
    x = np.random.randint(0, (2**depth) - 1, size=(256, 256), dtype=dtype)
    x = x.astype(decoding.color_depth_dtype_map[depth])

    data = decoding.compress_zip(x, depth, 1)
    y = decoding.decompress_zip(data, (256, 256), depth, 1)

    assert_array_equal(x, y)


@pytest.mark.parametrize("depth", (1, 8, 16, 32))
@pytest.mark.parametrize("version", (1, 2))
def test_rle(depth, version):
    np.random.seed(0)

    dtype = decoding.color_depth_dtype_map[depth]
    x = np.random.randint(0, (2**depth) - 1, size=(256, 256), dtype=dtype)
    x = x.astype(decoding.color_depth_dtype_map[depth])

    data = decoding.compress_rle(x, depth, version)
    y = decoding.decompress_rle(data, (256, 256), depth, version)

    assert_array_equal(x, y)
