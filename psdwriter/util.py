# -*- coding: utf-8 -*-


"""
Miscellaneous utilities.
"""


from functools import wraps
import math
import struct
import sys


DEBUG = True


def read_value(fd, fmt, endian='>'):
    """
    Read a single binary value from a file-like object.

    Parameters
    ----------
    fd : file-like object
        Must be opened for reading, in binary mode.

    fmt : str
        A `struct` module `format character
        <https://docs.python.org/2/library/struct.html#format-characters>`__.

    endian : str
        The endianness. Must be ``>`` or ``<``.  Default: ``>``.

    Returns
    -------
    value : any
        The value read from the file.
    """
    fmt = endian + fmt
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, fd.read(size))[0]


def write_value(fd, fmt, value, endian='>'):
    """
    Write a single binary value to a file-like object.

    Parameters
    ----------
    fd : file-like object
        Must be opened for writing, in binary mode.

    fmt : str
        A `struct` module `format character
        <https://docs.python.org/2/library/struct.html#format-characters>`__.

    value : any
        The value to encode and write to the file.

    endian : str
        The endianness. Must be ``>`` or ``<``.  Default: ``>``.
    """
    fmt = endian + fmt
    fd.write(struct.pack(fmt, value))


def pad(number, divisor):
    """
    Pads an integer up to the given divisor.
    """
    if number % divisor:
        number = (number // divisor + 1) * divisor
    return number


def read_pascal_string(fd, padding=1):
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
        return b''

    result = fd.read(length)

    padded_length = pad(length + 1, padding) - 1
    fd.seek(padded_length - length, 1)
    return result.decode('utf8', 'replace')


def write_pascal_string(fd, value, padding=1):
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
    write_value(fd, 'B', len(value))
    if len(value) == 0:
        fd.write(b'\0' * (padding - 1))
        return

    fd.write(value)

    padding = pad(length + 1, padding) - 1 - length
    if padding != 0:
        fd.write(b'\0' * padding)


def pascal_string_length(value, padding=1):
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
    """
    Decode Photoshop's definition of a `Unicode String
    <https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/#UnicodeStringDefine>`__.
    """
    return data[4:].decode('utf_16_be')


def encode_unicode_string(s):
    """
    Encode Photoshop's definition of a `Unicode String
    <https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/#UnicodeStringDefine>`__.
    """
    return struct.pack('>L', len(s)) + s.encode('utf_16_be')


def round_up(x, base=2):
    return int(base * math.ceil(float(x) / base))


_indent = [0]


def trace_read(func):
    """
    Prints debugging information from a read or write method.

    For internal use only.
    """
    @wraps(func)
    def wrapper(self, fd, *args):
        log('>>> {} @ {}', repr(self), fd.tell())
        _indent[0] += 1
        result = func(self, fd, *args)
        _indent[0] -= 1
        log('<<< {} @ {}', repr(self), fd.tell())
        return result

    return wrapper


trace_write = trace_read


def log(msg, *args):  # pragma: no cover
    """
    Print a logging message if debugging is turned on.
    """
    if DEBUG:
        print("  " * _indent[0], msg.format(*args))


def is_set_to_default(obj):
    """
    Returns ``True`` if a `traitlets.HasTraits` instance is set
    entirely to its defaults.
    """
    traits = obj.traits()
    for key, val in traits.items():
        if getattr(obj, key) != val.default_value:
            return False
    return True


def ensure_bigendian(arr):
    """
    Ensure that a Numpy array is in big-endian order.

    Returns a copy if the endianness needed to be changed.
    """
    order = arr.dtype.byteorder
    if order == '=':  # pragma: no cover
        if sys.byteorder == 'little':
            order = '<'
        else:
            order = '>'

    if order != '>':
        return arr.byteswap().view(arr.dtype.newbyteorder('>'))

    return arr


def unpack_bitflags(value, nbits):
    """
    Unpack a bitfield into its constituent parts.
    """
    return [bool(value & (1 << i)) for i in range(nbits)]


def pack_bitflags(*values):
    """
    Pack separate booleans back into a bit field.
    """
    result = 0
    for i, val in enumerate(values):
        if val:
            result |= (1 << i)
    return result
