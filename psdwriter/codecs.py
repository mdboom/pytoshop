# -*- coding: utf-8 -*-


"""
Coders and decoders for the various compression types in PSD.
"""


import zlib


import numpy as np


from . import enums
from . import util


_decompress_params = """
    Parameters
    ----------
    data : bytes
        The raw bytes from the file.

    shape : 2-tuple of int
        The shape of the resulting array, ``(height, width)``.

    depth : enums.ColorDepth
        The bit depth of the image. See `enums.ColorDepth`.

    version : enums.Version
        The version of the PSD file. See `enums.Version`.

    Returns
    -------
    image : numpy array
        The image data as a Numpy array.  If *depth* is 1, the array
        is expanded to ``uint8`` with a byte per pixel.
"""


_compress_params = """
    Parameters
    ----------
    image : 2-D numpy array
        The image to compress.  Must be unsigned integer with 8, 16 or
        32 bits.  If *depth* is 1, the array should have dtype
        ``uint8`` with a byte per pixel.

    depth : enums.ColorDepth
        The bit depth of the image. See `enums.ColorDepth`.

    version : enums.Version
        The version of the PSD file. See `enums.Version`.

    Returns
    -------
    data : bytes
        The raw bytes to write to the file.
"""


def decode_prediction(image):
    """
    Decode predictive coding in the image.

    Parameters
    ----------
    image : 2-D numpy array
        Must be unsigned 8- or 16-bit integer.

    Returns
    -------
    decoded : 2-D numpy array
        A copy of the array with the predictive coding decoded.
    """
    itemsize = image.dtype.itemsize

    if itemsize in (1, 2):
        image = image.copy()
        for x in range(image.shape[1] - 1):
            image[:, x+1] += image[:, x]
        return image

    elif itemsize == 4:
        # TODO
        raise ValueError(
            "zip with prediction for 32-bit images is not yet supported")

    else:
        raise ValueError(
            "Invalid itemsize {}".format(itemsize))


def encode_prediction(image):
    """
    Encode predictive coding in the image.

    Parameters
    ----------
    image : 2-D numpy array
        Must be unsigned 8- or 16-bit integer.

    Returns
    -------
    encoded : 2-D numpy array
        A copy of the array with the predictive coding.
    """
    itemsize = image.dtype.itemsize

    if itemsize in (1, 2):
        image = image.copy()
        for x in range(image.shape[1] - 1, 0, -1):
            image[:, x] -= image[:, x-1]
        return image

    elif itemsize == 4:
        # TODO
        raise ValueError(
            "zip with prediction for 32-bit images is not yet supported")

    else:
        raise ValueError(
            "Invalid itemsize {}".format(itemsize))


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
    """
    Converts raw data to a Numpy array.

{}
    """
    depth = enums.ColorDepth(depth)

    dtype = color_depth_dtype_map[depth]
    itemsize = color_depth_size_map[depth]

    # Truncate the data to a multiple of the dtype size
    data = data[:(len(data) // itemsize) * itemsize]

    arr = np.frombuffer(data, dtype)

    if depth == 1:
        # Unpack 1-bit image data
        arr = np.unpackbits(arr)

    # Resize the array in case the data is too short or too long
    size = shape[0] * shape[1]
    if size < arr.shape[0]:
        arr = arr[:size]
    elif size > arr.shape[0]:
        arr = np.resize(arr, (size,))

    # Make 2-dimensional
    image = arr.reshape(shape)
    return image
decompress_raw.__doc__ = decompress_raw.__doc__.format(_decompress_params)


def decompress_rle(data, shape, depth, version):
    """
    Decompress run length encoded data.

    Requires the `packbits <https://pypi.python.org/pypi/packbits/>`__
    library to be installed.

{}
    """
    try:
        import packbits
    except ImportError:  # pragma: no cover
        raise ImportError(
            "packbits must be installed to handle RLE compression")

    if version == 2:
        size = 4
        dtype = '>u4'
    else:
        size = 2
        dtype = '>u2'

    # Read the offset table
    offsets_length = size * shape[0]
    offsets = np.frombuffer(data[:offsets_length], dtype=dtype)
    data_size = int(np.sum(offsets))

    # Unpack the data itself
    data = packbits.decode(data[offsets_length:offsets_length + data_size])

    # Now pass along to the raw decoder to get a Numpy array
    return decompress_raw(data, shape, depth, version)
decompress_rle.__doc__ = decompress_rle.__doc__.format(_decompress_params)


def decompress_zip(data, shape, depth, version):
    """
    Decompress zip (zlib) encoded data.

{}
    """
    data = zlib.decompress(data)
    return decompress_raw(data, shape, depth, version)
decompress_zip.__doc__ = decompress_zip.__doc__.format(_decompress_params)


def decompress_zip_prediction(data, shape, depth, version):
    """
    Decompress zip (zlib) with prediction encoded data.

    Not supported for 1- or 32-bit images.

{}
    """
    if depth == 1:  # pragma: no cover
        raise ValueError(
            "zip with prediction is not supported for 1-bit images")

    data = zlib.decompress(data)
    image = decompress_raw(data, shape, depth, version)
    return decode_prediction(image)
decompress_zip_prediction.__doc__ = decompress_zip_prediction.__doc__.format(
    _decompress_params)


decompressors = {
    enums.Compression.raw: decompress_raw,
    enums.Compression.rle: decompress_rle,
    enums.Compression.zip: decompress_zip,
    enums.Compression.zip_prediction: decompress_zip_prediction
}


def decompress_image(data, compression, shape, depth, version):
    """
    Decompress data with the given compression.

    Parameters
    ----------
    data : bytes
        The raw bytes from the file.

    compression : enums.Compression
        The compression format to use.  See `enums.Compression`.

    shape : 2-tuple of int
        The shape of the resulting array, ``(height, width)``.

    depth : enums.ColorDepth
        The bit depth of the image. See `enums.ColorDepth`.

    version : enums.Version
        The version of the PSD file. See `enums.Version`.

    Returns
    -------
    image : numpy array
        The image data as a Numpy array.
    """
    compression = enums.Compression(compression)
    depth = enums.ColorDepth(depth)
    version = enums.Version(version)

    return decompressors[compression](data, shape, depth, version)


def compress_raw(image, depth, version):
    """
    Convert a Numpy array to raw bytes to save in the file.

{}
    """
    if depth == 1:
        image = np.packbits(image.flatten())
    return image.tobytes()
compress_raw.__doc__ = compress_raw.__doc__.format(_compress_params)


def compress_rle(image, depth, version):
    """
    Convert a Numpy array to a run length encoded stream.

    Requires the `packbits <https://pypi.python.org/pypi/packbits/>`__
    library to be installed.

{}
    """
    try:
        import packbits
    except ImportError:  # pragma: no cover
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
compress_rle.__doc__ = compress_rle.__doc__.format(_compress_params)


def compress_zip(image, depth, version):
    """
    Compress a Numpy array to a zip (zlib) compressed stream.

{}
    """
    data = compress_raw(image, depth, version)
    return zlib.compress(data)
compress_zip.__doc__ = compress_zip.__doc__.format(_compress_params)


def compress_zip_prediction(image, depth, version):
    """
    Compress a Numpy array to a zip (zlib) with prediction compressed
    stream.

    Not supported for 1- or 32-bit images.

{}
    """
    if depth == 1:  # pragma: no cover
        raise ValueError(
            "zip with prediction is not supported for 1-bit images")

    data = compress_raw(image, depth, version)
    data = encode_prediction(image)
    return zlib.compress(data)
compress_zip_prediction.__doc__ = compress_zip_prediction.__doc__.format(
    _compress_params)


compressors = {
    enums.Compression.raw: compress_raw,
    enums.Compression.rle: compress_rle,
    enums.Compression.zip: compress_zip,
    enums.Compression.zip_prediction: compress_zip_prediction
}


def compress_image(image, compression, depth, version):
    """
    Compress an image with the given compression type.

    Parameters
    ----------
    image : 2-D numpy array
        The image to compress.  Must be unsigned integer with 8, 16 or
        32 bits.  If *depth* is 1, the array should have dtype
        ``uint8`` with a byte per pixel.

    compression : enums.Compression
        The compression format to use.  See `enums.Compression`.

    depth : enums.ColorDepth
        The bit depth of the image. See `enums.ColorDepth`.

    version : enums.Version
        The version of the PSD file. See `enums.Version`.

    Returns
    -------
    data : bytes
        The raw bytes to write to the file.
    """
    dtype = image.dtype
    if dtype.kind != 'u':
        raise ValueError("Image array dtype must be unsigned int")
    if dtype.itemsize != color_depth_size_map[depth]:
        raise ValueError("Image array values of wrong size")
    image = util.ensure_bigendian(image)

    return compressors[compression](image, depth, version)
