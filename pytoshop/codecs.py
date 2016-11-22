# -*- coding: utf-8 -*-


"""
Coders and decoders for the various compression types in PSD.
"""


import zlib


import numpy as np


from . import enums
from . import packbits
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
    fd : file-like object
        Writable file-like object, open in binary mode.

    image : 2-D numpy array
        The image to compress.  Must be unsigned integer with 8, 16 or
        32 bits.  If *depth* is 1, the array should have dtype
        ``uint8`` with a byte per pixel.

    depth : enums.ColorDepth
        The bit depth of the image. See `enums.ColorDepth`.

    version : enums.Version
        The version of the PSD file. See `enums.Version`.
"""


_compress_constant_params = """
    Parameters
    ----------
    fd : file-like object
        Writable file-like object, open in binary mode.

    value : int
        The constant value in the generated virtual image.

    width : int
        The width of the image, in pixels.

    rows : int
        The number of rows in the image, in pixels.  This is
        ``height * num_channels``.

    depth : enums.ColorDepth
        The bit depth of the image. See `enums.ColorDepth`.

    version : enums.Version
        The version of the PSD file. See `enums.Version`.
"""


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

    # Make 2-dimensional
    image = arr.reshape(shape)
    return image
decompress_raw.__doc__ = decompress_raw.__doc__.format(_decompress_params)


def decompress_rle(data, shape, depth, version):
    """
    Decompress run length encoded data.

{}
    """
    if version == 2:
        size = 4
        dtype = '>u4'
    else:
        size = 2
        dtype = '>u2'

    # Read the offset table
    offsets_length = size * shape[0]
    offsets = np.frombuffer(data[:offsets_length], dtype=dtype)
    stride = color_depth_size_map[depth] * shape[1]

    # Unpack the data itself
    i = offsets_length
    result = []
    for offset in offsets:
        chunk = packbits.decode(data[i:i+offset], stride)
        result.append(chunk)
        i += offset

    # Now pass along to the raw decoder to get a Numpy array
    return decompress_raw(b''.join(result), shape, depth, version)
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
    elif depth == 32:
        raise ValueError(
            "zip with prediction is not implemented for 32-bit images")
    elif depth == 8:
        decoder = packbits.decode_prediction_8bit
    else:
        decoder = packbits.decode_prediction_16bit

    data = zlib.decompress(data)
    image = util.ensure_native_endian(
        decompress_raw(data, shape, depth, version))
    for i in range(len(image)):
        decoder(image[i].flatten())
    return image
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


def normalize_image(image, depth):
    if depth == 1:
        image = np.packbits(image.flatten())
    return image


def compress_raw(fd, image, depth, version):
    """
    Write a Numpy array to raw bytes in a file.

{}
    """
    image = normalize_image(image, depth)
    for row in image:
        fd.write(row)
compress_raw.__doc__ = compress_raw.__doc__.format(_compress_params)


def compress_rle(fd, image, depth, version):
    """
    Write a Numpy array to a run length encoded stream.

{}
    """
    if depth == 1:  # pragma: no cover
        raise ValueError(
            "rle compression is not supported for 1-bit images")

    start = fd.tell()
    if version == 1:
        fd.seek(image.shape[0] * 2, 1)
        lengths = np.empty((len(image),), dtype='>u2')
    else:
        fd.seek(image.shape[0] * 4, 1)
        lengths = np.empty((len(image),), dtype='>u4')

    for i, row in enumerate(image):
        packed = packbits.encode(row.tobytes())
        lengths[i] = len(packed)
        fd.write(packed)

    end = fd.tell()
    fd.seek(start)
    fd.write(lengths.tobytes())
    fd.seek(end)
compress_rle.__doc__ = compress_rle.__doc__.format(_compress_params)


def compress_zip(fd, image, depth, version):
    """
    Write a Numpy array to a zip (zlib) compressed stream.

{}
    """
    image = normalize_image(image, depth)
    compressor = zlib.compressobj()
    for row in image:
        fd.write(compressor.compress(row))
    fd.write(compressor.flush())
compress_zip.__doc__ = compress_zip.__doc__.format(_compress_params)


def compress_zip_prediction(fd, image, depth, version):
    """
    Write a Numpy array to a zip (zlib) with prediction compressed
    stream.

    Not supported for 1- or 32-bit images.

{}
    """
    if depth == 1:  # pragma: no cover
        raise ValueError(
            "zip with prediction is not supported for 1-bit images")
    elif depth == 32:  # pragma: no cover
        raise ValueError(
            "zip with prediction is not implemented for 32-bit images")
    elif depth == 8:
        encoder = packbits.encode_prediction_8bit
    elif depth == 16:
        encoder = packbits.encode_prediction_16bit

    compressor = zlib.compressobj()
    for row in image:
        row = util.ensure_native_endian(row)
        encoder(row.flatten())
        row = util.ensure_bigendian(row)
        fd.write(compressor.compress(row))
    fd.write(compressor.flush())
compress_zip_prediction.__doc__ = compress_zip_prediction.__doc__.format(
    _compress_params)


compressors = {
    enums.Compression.raw: compress_raw,
    enums.Compression.rle: compress_rle,
    enums.Compression.zip: compress_zip,
    enums.Compression.zip_prediction: compress_zip_prediction
}


def compress_image(fd, image, compression, shape, num_channels, depth,
                   version):
    """
    Write an image with the given compression type.

    Parameters
    ----------
    fd : file-like object
        Writable file-like object, open in binary mode.

    image : 2-D numpy array or scalar
        The image to compress.  Must be unsigned integer with 8, 16 or
        32 bits.  If *depth* is 1, the array should have dtype
        ``uint8`` with a byte per pixel.  If a scalar, a "virtual"
        image will be used as if the image contained only that
        constant value.

    compression : enums.Compression
        The compression format to use.  See `enums.Compression`.

    shape : 2-tuple of int
        The shape of the image ``(height, width)``.  If *image* is an
        array, the *shape* is used to confirm it has the correct
        shape.  If *image* is a constant, *shape* is used to generate
        the virtual constant image.

    num_channels : int
        The number of color channels in the image.  If *image* is an
        array, the *num_channels* is used to confirm it has the
        correct number of channels.  If *image* is a constant,
        *num_channels* is used to generate the virtual constant image.

    depth : enums.ColorDepth
        The bit depth of the image. See `enums.ColorDepth`.  If
        *image* is an array, the *depth* is used to confirm it has the
        correct number of channels.  If *image* is a constant, *depth*
        is used to generate the virtual constant image.

    version : enums.Version
        The version of the PSD file. See `enums.Version`.
    """
    if isinstance(image, int):
        image = np.dtype(color_depth_dtype_map[depth]).type(image)

    dtype = image.dtype
    if dtype.kind != 'u':
        raise ValueError("Image array dtype must be unsigned int")
    if dtype.itemsize != color_depth_size_map[depth]:
        raise ValueError("Image array values of wrong size")

    if np.isscalar(image):
        width = shape[1]
        rows = shape[0] * num_channels
        return constant_compressors[compression](
            fd, image, width, rows, depth, version)
    else:
        acceptable_shapes = [
            (num_channels, shape[0], shape[1]),
            (num_channels * shape[0], shape[1])
        ]

        if image.shape not in acceptable_shapes:
            raise ValueError("Image is the wrong shape")

        image = np.asarray(image)
        image = util.ensure_bigendian(image)
        image = image.reshape((shape[0] * num_channels, shape[1]))
        return compressors[compression](fd, image, depth, version)


def _make_onebit_constant(value, width, rows):
    if value:
        value == 255
    else:
        value = 0
    return np.ones((width, rows), np.uint8) * value


def _make_constant_row(value, width, depth):
    return util.ensure_bigendian(
        np.ones((width,), dtype=color_depth_dtype_map[depth]) * value)


def compress_constant_raw(fd, value, width, rows, depth, version):
    """
    Write a virtual image containing a constant to a raw
    stream.

{}
    """
    if depth == 1:
        image = _make_onebit_constant(value, width, rows)
        compress_raw(fd, image, depth, version)
    else:
        row = _make_constant_row(value, width, depth)
        row = row.tobytes()
        for i in range(rows):
            fd.write(row)
compress_constant_raw.__doc__ = compress_constant_raw.__doc__.format(
    _compress_constant_params)


def compress_constant_rle(fd, value, width, rows, depth, version):
    """
    Write a virtual image containing a constant to a runlength-encoded
    stream.

{}
    """
    if depth == 1:  # pragma: no cover
        raise ValueError(
            "rle compression is not supported for 1-bit images")

    row = _make_constant_row(value, width, depth)
    packed = packbits.encode(row.tobytes())

    if version == 1:
        for i in range(rows):
            util.write_value(fd, 'H', len(packed))
    else:
        for i in range(rows):
            util.write_value(fd, 'I', len(packed))

    for i in range(rows):
        fd.write(packed)
compress_constant_rle.__doc__ = compress_constant_rle.__doc__.format(
    _compress_constant_params)


def compress_constant_zip(fd, value, width, rows, depth, version):
    """
    Write a virtual image containing a constant to a zip compressed
    stream.

{}
    """
    if depth == 1:
        image = _make_onebit_constant(value, width, rows)
        compress_zip(fd, image, depth, version)
    else:
        row = _make_constant_row(value, width, depth)
        row = row.tobytes()
        compressor = zlib.compressobj()
        for i in range(rows):
            fd.write(compressor.compress(row))
        fd.write(compressor.flush())
compress_constant_zip.__doc__ = compress_constant_zip.__doc__.format(
    _compress_constant_params)


def compress_constant_zip_prediction(
        fd, value, width, rows, depth, version):
    """
    Write a virtual image containing a constant to a zip with
    prediction compressed stream.

{}
    """
    if depth == 1:  # pragma: no cover
        raise ValueError(
            "zip with prediction is not supported for 1-bit images")
    elif depth == 32:  # pragma: no cover
        raise ValueError(
            "zip with prediction is not implemented for 32-bit images")
    elif depth == 8:
        encoder = packbits.encode_prediction_8bit
    elif depth == 16:
        encoder = packbits.encode_prediction_16bit

    row = _make_constant_row(value, width, depth)
    row = row.reshape((1, width))
    row = util.ensure_native_endian(row)
    encoder(row.flatten())
    row = util.ensure_bigendian(row)
    row = row.tobytes()
    compressor = zlib.compressobj()
    for i in range(rows):
        fd.write(compressor.compress(row))
    fd.write(compressor.flush())
compress_constant_zip_prediction.__doc__ = \
    compress_constant_zip_prediction.__doc__.format(
        _compress_constant_params)


constant_compressors = {
    enums.Compression.raw: compress_constant_raw,
    enums.Compression.rle: compress_constant_rle,
    enums.Compression.zip: compress_constant_zip,
    enums.Compression.zip_prediction: compress_constant_zip_prediction
}
