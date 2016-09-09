# -*- coding: utf-8 -*-


from functools import wraps
import math
import struct


DEBUG = True


def read_value(fd, fmt, endian='>'):
    fmt = endian + fmt
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, fd.read(size))[0]


def write_value(fd, fmt, value, endian='>'):
    fmt = endian + fmt
    fd.write(struct.pack(fmt, value))


def pad(number, divisor):
    if number % divisor:
        number = (number // divisor + 1) * divisor
    return number


def read_pascal_string(fd, padding=1):
    length = read_value(fd, 'B')
    if length == 0:
        fd.seek(padding - 1, 1)
        return b''

    result = fd.read(length)

    padded_length = pad(length + 1, padding) - 1
    fd.seek(padded_length - length, 1)
    return result.decode('utf8', 'replace')


def write_pascal_string(fd, value, padding=1):
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
    value = value.encode('utf8')

    if len(value) == 0:
        return padding

    length = len(value)
    padding = pad(length + 1, padding) - 1 - length
    return length + padding + 1


class BinaryStruct(object):
    """
    A wrapper around the Python stdlib struct module to define a
    binary struct more like a dictionary than a tuple.
    """
    def __init__(self, descr, endian='>'):
        """
        Parameters
        ----------
        descr : list of tuple
            Each entry is a pair ``(name, format)``, where ``format``
            is one of the format types understood by `struct`.
        endian : str, optional
            The endianness of the struct.  Must be ``>`` or ``<``.
        """
        self._fmt = [endian]
        self._offsets = {}
        self._names = []
        i = 0
        for name, fmt in descr:
            self._fmt.append(fmt)
            self._offsets[name] = (i, (endian + fmt).encode('ascii'))
            self._names.append(name)
            i += struct.calcsize(fmt.encode('ascii'))
        self._fmt = ''.join(self._fmt).encode('ascii')
        self._size = struct.calcsize(self._fmt)

    @property
    def size(self):
        """
        Return the size of the struct.
        """
        return self._size

    def pack(self, **kwargs):
        """
        Pack the given arguments, which are given as kwargs, and
        return the binary struct.
        """
        fields = [0] * len(self._names)
        for i, key in enumerate(self._names):
            if key in kwargs:
                fields[i] = kwargs[key]
            else:
                raise ValueError("Missing key '{}'".format(key))
        return struct.pack(self._fmt, *fields)

    def pack_object(self, obj):
        """
        Pack the given object with attributes and return the binary
        struct.
        """
        fields = [0] * len(self._names)
        for i, key in enumerate(self._names):
            if hasattr(obj, key):
                fields[i] = getattr(obj, key)
            else:
                raise ValueError("Missing attribute '{}'".format(key))
        return struct.pack(self._fmt, *fields)

    def unpack(self, buff):
        """
        Unpack the given binary buffer into the fields.  The result
        is a dictionary mapping field names to values.
        """
        args = struct.unpack_from(self._fmt, buff[:self._size])
        return dict(zip(self._names, args))

    def read(self, fd):
        """
        Read a struct from the current location in the file.
        """
        buff = fd.read(self.size)
        return self.unpack(buff)

    def write(self, fd, obj):
        """
        Write a struct to the current location in the file.
        """
        buff = self.pack_object(obj)
        fd.write(buff)


def round_up(x, base=2):
    return int(base * math.ceil(float(x) / base))


def pad_block(func):
    @wraps(func)
    def wrapper(self, fd, header):
        length = self.total_length(header)
        end = fd.tell() + length
        func(self, fd, header)
        extra = end - fd.tell()
        if extra > 0:
            fd.write(b'\0' * extra)

    return wrapper


_indent = [0]


def trace_read(func):
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


def log(msg, *args):
    if DEBUG:
        print("  " * _indent[0], msg.format(*args))


class DeferredLoad:
    def __init__(self, data):
        if isinstance(data, bytes):
            self._data = data
            self._data_length = len(data)
        elif isinstance(data, tuple):
            self._data = None
            self._fd = data[0]
            self._data_offset = data[1]
            self._data_length = data[2]
        else:
            raise TypeError("data is invalid type")

    @property
    def data_length(self):
        return self._data_length

    @property
    def data(self):
        if self._data is None:
            start = self._fd.tell()
            self._fd.seek(self._data_offset, 0)
            self._data = self._fd.read(self._data_length)
            self._fd.seek(start, 0)
        return self._data

    @data.setter
    def data(self, value):
        if not isinstance(value, bytes):
            raise TypeError("data must be bytes")
        self._data = value
        self._data_length = len(value)


def is_set_to_default(obj):
    traits = obj.traits()
    for key, val in traits.items():
        if getattr(obj, key) != val.default_value:
            return False
    return True
