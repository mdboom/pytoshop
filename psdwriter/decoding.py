# -*- coding: utf-8 -*-


import zlib


import numpy as np


from . import enums
from . import util


def decode_prediction(image, depth):
    def delta_decode(img):
        img = img.copy()
        for x in range(img.shape[1] - 1):
            img[:, x+1] += img[:, x]
        return img

    if depth in (8, 16):
        return delta_decode(image)

    elif depth == 32:
        # TODO
        raise ValueError(
            "zip with prediction for 32-bit images is not yet supported")

    else:
        raise ValueError(
            "zip with prediction is not supported for 1-bit images")


def encode_prediction(image, depth):
    def delta_encode(img):
        img = img.copy()
        for x in range(img.shape[1] - 1, 0, -1):
            img[:, x] -= img[:, x-1]
        return img

    if depth in (8, 16):
        return delta_encode(image)

    elif depth == 32:
        # TODO
        raise ValueError(
            "zip with prediction for 32-bit images is not yet supported")

    else:
        raise ValueError(
            "zip with prediction is not supported for 1-bit images")


color_depth_dtype_map = {
    1: 'u1',
    8: 'u1',
    16: '>u2',
    32: '>u4'
}


color_depth_size_map = {
    1: 1,
    8: 1,
    16: 2,
    32: 4
}


def decompress_raw(data, shape, depth, version):
    dtype = color_depth_dtype_map[depth]
    size = color_depth_size_map[depth]
    data = data[:(len(data) // size) * size]
    arr = np.frombuffer(data, dtype)
    if depth == 1:
        arr = np.unpackbits(arr)
    size = shape[0] * shape[1]
    if size < arr.shape[0]:
        arr = arr[:size]
    elif size > arr.shape[0]:
        arr = np.resize(arr, (size,))
    image = arr.reshape(shape)
    return image


def decompress_rle(data, shape, depth, version):
    try:
        import packbits
    except ImportError:
        raise ImportError(
            "packbits must be installed to handle RLE compression")

    if version == 2:
        size = 4
        dtype = '>u4'
    else:
        size = 2
        dtype = '>u2'

    offsets_length = size * shape[0]
    offsets = np.frombuffer(data[:offsets_length], dtype=dtype)
    data_size = int(np.sum(offsets))

    data = packbits.decode(data[offsets_length:offsets_length + data_size])

    return decompress_raw(data, shape, depth, version)


def decompress_zip(data, shape, depth, version):
    data = zlib.decompress(data)
    return decompress_raw(data, shape, depth, version)


def decompress_zip_prediction(data, shape, depth, version):
    if depth == 1:
        raise ValueError(
            "zip with prediction is not supported for 1-bit images")

    data = zlib.decompress(data)
    image = decompress_raw(data, shape, depth, version)
    return decode_prediction(image, depth)


decompressors = {
    enums.Compression.raw: decompress_raw,
    enums.Compression.rle: decompress_rle,
    enums.Compression.zip: decompress_zip,
    enums.Compression.zip_prediction: decompress_zip_prediction
}


def decompress_image(data, compression, shape, depth, version):
    return decompressors[compression](data, shape, depth, version)


def compress_raw(image, depth, version):
    if depth == 1:
        image = np.packbits(image.flatten())
    return image.tobytes()


def compress_rle(image, depth, version):
    try:
        import packbits
    except ImportError:
        raise ImportError(
            "packbits must be installed to handle RLE compression")

    if version == 2:
        dtype = '>u4'
    else:
        dtype = '>u2'

    offsets = np.zeros(image.shape[0], dtype=dtype)
    packed_rows = []
    for i, row in enumerate(image):
        data = compress_raw(row, depth, version)
        packed = packbits.encode(data)
        offsets[i] = len(packed)
        packed_rows.append(packed)

    return offsets.tobytes() + b''.join(packed_rows)


def compress_zip(image, depth, version):
    data = compress_raw(image, depth, version)
    return zlib.compress(data)


def compress_zip_prediction(image, depth, version):
    data = compress_raw(image, depth, version)
    data = encode_prediction(image, depth)
    return zlib.compress(data)


compressors = {
    enums.Compression.raw: compress_raw,
    enums.Compression.rle: compress_rle,
    enums.Compression.zip: compress_zip,
    enums.Compression.zip_prediction: compress_zip_prediction
}


def compress_image(image, compression, depth, version):
    dtype = image.dtype
    if dtype.kind != 'u':
        raise ValueError("Image array dtype must be unsigned int")
    if dtype.itemsize != color_depth_size_map[depth]:
        raise ValueError("Image array values of wrong size")
    image = util.ensure_bigendian(image)

    return compressors[compression](image, depth, version)


def interlace_image(image, width, height, num_channels):
    result = np.empty(
        (height, width, num_channels),
        dtype=image.dtype)
    image = image.reshape((num_channels, height, width))

    for i in range(num_channels):
        result[:, :, i] = image[i]

    return result


def deinterlace_image(image, width, height, num_channels):
    result = np.empty(
        (num_channels, height, width),
        dtype=image.dtype)

    for i in range(num_channels):
        result[i] = image[:, :, i]

    result = result.reshape((height * num_channels, width))

    return result
