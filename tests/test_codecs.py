# -*- coding: utf-8 -*-


import io


import numpy as np
from numpy.testing import assert_array_equal
import pytest


from pytoshop import codecs
from pytoshop import enums


@pytest.mark.parametrize("depth", (8, 16))
def test_zip_with_prediction(depth):
    np.random.seed(0)

    dtype = codecs.color_depth_dtype_map[depth]
    x = np.random.randint(0, (2**depth) - 1, size=(255, 256), dtype=dtype)

    fd = io.BytesIO()
    codecs.compress_image(
        fd, x, enums.Compression.zip_prediction, (255, 256), 1, depth, 1)
    y = codecs.decompress_image(
        fd.getvalue(), enums.Compression.zip_prediction, (255, 256), depth, 1)

    assert_array_equal(x, y)


@pytest.mark.parametrize("depth", (1, 8, 16, 32))
def test_zip(depth):
    np.random.seed(0)

    dtype = codecs.color_depth_dtype_map[depth]
    x = np.random.randint(0, (2**depth) - 1, size=(255, 256), dtype=dtype)

    fd = io.BytesIO()
    codecs.compress_image(
        fd, x, enums.Compression.zip, (255, 256), 1, depth, 1)
    y = codecs.decompress_image(
        fd.getvalue(), enums.Compression.zip, (255, 256), depth, 1)

    assert_array_equal(x, y)


@pytest.mark.parametrize("depth", (8, 16, 32))
@pytest.mark.parametrize("version", (1, 2))
def test_rle(depth, version):
    np.random.seed(0)

    dtype = codecs.color_depth_dtype_map[depth]
    x = np.random.randint(0, (2**depth) - 1, size=(255, 256), dtype=dtype)

    fd = io.BytesIO()
    codecs.compress_image(
        fd, x, enums.Compression.rle, (255, 256), 1, depth, version)
    y = codecs.decompress_image(
        fd.getvalue(), enums.Compression.rle, (255, 256), depth, version)

    assert_array_equal(x, y)


@pytest.mark.parametrize("depth", (1, 8, 16, 32))
def test_raw_constant(depth):
    if depth == 1:
        value = 1
    else:
        value = 42

    dtype = codecs.color_depth_dtype_map[depth]
    x = np.ones((255, 256), dtype=dtype) * value

    fd = io.BytesIO()
    codecs.compress_image(
        fd, value, enums.Compression.raw, (255, 256), 1, depth, 1)
    y = codecs.decompress_image(
        fd.getvalue(), enums.Compression.raw, (255, 256), depth, 1)

    assert_array_equal(x, y)


@pytest.mark.parametrize("depth", (8, 16))
def test_zip_with_prediction_constant(depth):
    dtype = codecs.color_depth_dtype_map[depth]
    x = np.ones((255, 256), dtype=dtype) * 42

    fd = io.BytesIO()
    codecs.compress_image(
        fd, 42, enums.Compression.zip_prediction, (255, 256), 1, depth, 1)
    y = codecs.decompress_image(
        fd.getvalue(), enums.Compression.zip_prediction, (255, 256), depth, 1)

    assert_array_equal(x, y)


@pytest.mark.parametrize("depth", (1, 8, 16, 32))
def test_zip_constant(depth):
    if depth == 1:
        value = 1
    else:
        value = 42

    dtype = codecs.color_depth_dtype_map[depth]
    x = np.ones((255, 256), dtype=dtype) * value

    fd = io.BytesIO()
    codecs.compress_image(
        fd, value, enums.Compression.zip, (255, 256), 1, depth, 1)
    y = codecs.decompress_image(
        fd.getvalue(), enums.Compression.zip, (255, 256), depth, 1)

    assert_array_equal(x, y)


@pytest.mark.parametrize("depth", (8, 16, 32))
@pytest.mark.parametrize("version", (1, 2))
def test_rle_constant(depth, version):
    dtype = codecs.color_depth_dtype_map[depth]
    x = np.ones((255, 256), dtype=dtype) * 42

    fd = io.BytesIO()
    codecs.compress_image(
        fd, 42, enums.Compression.rle, (255, 256), 1, depth, version)
    y = codecs.decompress_image(
        fd.getvalue(), enums.Compression.rle, (255, 256), depth, version)

    assert_array_equal(x, y)
