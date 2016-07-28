# -*- coding: utf-8 -*-


from functools import wraps
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
    return result


def write_pascal_string(fd, value, padding=1):
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
    return int(base * round(float(x) / base))


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


def trace_read(func):
    @wraps(func)
    def wrapper(self, fd, *args):
        print(">>>", self, fd.tell())
        result = func(self, fd, *args)
        print("<<<", self, fd.tell())
        return result

    if DEBUG:
        return wrapper
    else:
        return func
