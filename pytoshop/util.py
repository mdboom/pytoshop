# -*- coding: utf-8 -*-


"""
Miscellaneous utilities.
"""


from __future__ import unicode_literals, absolute_import


from functools import wraps
import struct
import sys


from . import enums


from typing import Any, BinaryIO, Callable, List, Type, TYPE_CHECKING  # NOQA
if TYPE_CHECKING:
    import numpy as np  # NOQA


DEBUG = False


def read_value(fd, fmt, endian='>'):
    # type: (BinaryIO, unicode, unicode) -> Any
    """
    Read a values from a file-like object.

    Parameters
    ----------
    fd : file-like object
        Must be opened for reading, in binary mode.

    fmt : str
        A `struct` module `format character
        <https://docs.python.org/2/library/struct.html#format-characters>`__
        string.

    endian : str
        The endianness. Must be ``>`` or ``<``.  Default: ``>``.

    Returns
    -------
    value : any
        The value(s) read from the file.

        If a single value, it is returned alone.  If multiple values,
        a tuple is returned.
    """
    fmt = endian + fmt
    size = struct.calcsize(fmt)  # type: ignore
    result = struct.unpack(fmt, fd.read(size))  # type: ignore
    if len(result) == 1:
        return result[0]
    else:
        return result


def write_value(fd, fmt, *value, **kwargs):
    """
    Write a single binary value to a file-like object.

    Parameters
    ----------
    fd : file-like object
        Must be opened for writing, in binary mode.

    fmt : str
        A `struct` module `format character
        <https://docs.python.org/2/library/struct.html#format-characters>`__
        string.

    value : any
        The value to encode and write to the file.

    endian : str
        The endianness. Must be ``>`` or ``<``.  Default: ``>``.
    """
    endian = kwargs.get('endian', '>')
    fmt = endian + fmt
    fd.write(struct.pack(fmt, *value))


def pad(number, divisor):
    # type: (int, int) -> int
    """
    Pads an integer up to the given divisor.
    """
    if number % divisor:
        number = (number // divisor + 1) * divisor
    return number


def read_pascal_string(fd, padding=1):
    # type: (BinaryIO, int) -> unicode
    """
    Read a UTF-8-encoded Pascal string from a file.

    Parameters
    ----------
    fd : file-like object
        Must be opened for reading, seekable and in binary mode.

    padding : int, optional
        If provided, additional pad bytes will be read until
        the total amount read is a multiple of padding.

    Returns
    -------
    value : str
        The unicode value of the string.
    """
    length = read_value(fd, 'B')
    if length == 0:
        fd.seek(padding - 1, 1)
        return ''

    result = fd.read(length)

    padded_length = pad(length + 1, padding) - 1
    fd.seek(padded_length - length, 1)
    return result.decode('utf8', 'replace')


def write_pascal_string(fd, value, padding=1):
    # type: (BinaryIO, unicode, int) -> None
    """
    Write a UTF-8-encoded Pascal string to a file.

    Parameters
    ----------
    fd : file-like object
        Must be opened for writing and in binary mode.

    value : str
        A unicode string value.

    padding : int, optional
        If provided, additional pad bytes will be written until
        the total amount written is a multiple of padding.
    """
    value = value.encode('utf8')

    length = len(value)
    if length > 255:
        value = value[:255]
        length = 255

    write_value(fd, 'B', len(value))
    if len(value) == 0:
        fd.write(b'\0' * (padding - 1))
        return

    fd.write(value)

    padding = pad(length + 1, padding) - 1 - length
    if padding != 0:
        fd.write(b'\0' * padding)


def pascal_string_length(value, padding=1):
    # type: (unicode, int) -> int
    """
    Calculates the total length of writing a UTF-8-encoded Pascal
    string to disk.

    Parameters
    ----------
    value : str
        A unicode string value.

    Returns
    -------
    length : int
        The length, in bytes.
    """
    value = value.encode('utf8')

    if len(value) == 0:
        return padding

    length = len(value)
    padding = pad(length + 1, padding) - 1 - length
    return length + padding + 1


def decode_unicode_string(data):
    # type: (bytes) -> unicode
    """
    Decode Photoshop's definition of a `Unicode String
    <https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/#UnicodeStringDefine>`__.
    """
    return data[4:].rstrip(b'\0').decode('utf_16_be')


def encode_unicode_string(s):
    # type: (unicode) -> bytes
    """
    Encode Photoshop's definition of a `Unicode String
    <https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/#UnicodeStringDefine>`__.
    """
    return (struct.pack('>L', len(s) + 1)  # type: ignore
            + s.encode('utf_16_be') + b'\0\0')


def read_unicode_string(fd):
    # type: (BinaryIO) -> unicode
    """
    Read a UTF-16-BE-encoded Unicode string (with length) from a file.

    Parameters
    ----------
    fd : file-like object
        Must be opened for reading, seekable and in binary mode.

    Returns
    -------
    value : str
        The unicode value of the string.
    """
    length = read_value(fd, 'L')
    data = fd.read(length * 2)
    return data.rstrip(b'\0').decode('utf_16_be')


def write_unicode_string(fd, value):
    # type: (BinaryIO, unicode) -> None
    """
    Write a UTF-16-BE-encoded Unicode string (with length) to a file.

    Parameters
    ----------
    fd : file-like object
        Must be opened for writing and in binary mode.

    value : str
        A unicode string value.
    """
    fd.write(encode_unicode_string(value))


def unicode_string_length(value):
    # type: (unicode) -> int
    """
    Calculates the total length of writing a UTF-16-BE-encoded Unicode
    string (with length) to a file.

    Parameters
    ----------
    value : str
        A unicode string value.

    Returns
    -------
    length : int
        The length, in bytes.
    """
    return len(encode_unicode_string(value))


_indent = [0]


def trace_read(func):  # pragma: no cover
    """
    Prints debugging information from a read or write method.

    For internal use only.
    """
    @wraps(func)
    def wrapper(self, fd, *args):
        if isinstance(self, type):
            name = self.__name__
        else:
            name = self.__class__.__name__
        log('>>> {} @ {}', name, fd.tell())
        _indent[0] += 1
        result = func(self, fd, *args)
        _indent[0] -= 1
        log('<<< {} @ {}', name, fd.tell())
        return result

    if DEBUG:
        return wrapper
    else:
        return func


trace_write = trace_read


def log(msg, *args):  # pragma: no cover
    """
    Print a logging message if debugging is turned on.
    """
    if DEBUG:
        print("  " * _indent[0], msg.format(*args))


def do_byteswap(arr):
    # type: (np.ndarray) -> np.ndarray
    """
    Return a copy of an array, byteswapped.
    """
    return arr.byteswap().view(arr.dtype.newbyteorder('>'))


def ensure_bigendian(arr):
    # type: (np.ndarray) -> np.ndarray
    """
    Ensure that a Numpy array is in big-endian order.

    Returns a copy if the endianness needed to be changed.
    """
    if needs_byteswap(arr):
        return do_byteswap(arr)
    return arr


if sys.byteorder == 'little':
    def needs_byteswap(arr):
        # type: (np.ndarray) -> bool
        """
        Returns True if the array needs to be byteswapped.
        """
        order = arr.dtype.byteorder
        return order in ('<', '=')
else:
    def needs_byteswap(arr):
        # type: (np.ndarray) -> bool
        """
        Returns True if the array needs to be byteswapped.
        """
        order = arr.dtype.byteorder
        return order == '<'


def ensure_native_endian(arr):
    # type: (np.ndarray) -> np.ndarray
    """
    Ensure that a Numpy array is in native-endian order.

    Returns a copy if the endianness needed to be changed.
    """
    order = arr.dtype.byteorder

    if order != '=':
        return arr.byteswap().view(arr.dtype.newbyteorder('='))

    return arr


def unpack_bitflags(value, nbits):
    # type: (int, int) -> List[bool]
    """
    Unpack a bitfield into its constituent parts.
    """
    return [bool(value & (1 << i)) for i in range(nbits)]


def pack_bitflags(*values):
    # type: (*bool) -> int
    """
    Pack separate booleans back into a bit field.
    """
    result = 0
    for i, val in enumerate(values):
        if val:
            result |= (1 << i)
    return result


def assert_is_list_of(value, cls, min=None, max=None):
    # type: (Any, Type, int, int) -> None
    """
    If value is not a list of cls instances, raises TypeError.
    """
    if not isinstance(value, list):
        raise TypeError("Must be list of {}".format(cls.__name__))
    for item in value:
        if not isinstance(item, cls):
            raise TypeError("Must be list of {}".format(cls.__name__))
        if ((min is not None and item < min) or
                (max is not None and item > max)):
            raise ValueError(
                "All values must be in range {} to {}".format(min, max)
            )


def _get_channel_id(color, color_mode):
    if color not in enums.ColorChannelMapping:
        raise ValueError("Unknown color '{}'".format(color))

    exp_color_mode, channel_id = enums.ColorChannelMapping[color]
    if exp_color_mode is not None and exp_color_mode != color_mode:
        raise ValueError(
            "Color '{!s}' is not valid for color mode '{!s}', "
            "expected '{!s}'".format(
                color, color_mode, exp_color_mode)
        )

    return channel_id


def get_channel(color, color_mode, channels):
    channel_id = _get_channel_id(color, color_mode)
    return channels[channel_id]


def set_channel(color, channel, color_mode, channels):
    channel_id = _get_channel_id(color, color_mode)
    channels[channel_id] = channel
