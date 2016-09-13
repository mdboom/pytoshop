# -*- coding: utf-8 -*-


from functools import wraps
import math
import struct
import sys


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


def decode_unicode_string(data):
    return data[4:].decode('utf_16_be')


def encode_unicode_string(s):
    return struct.pack('>L', len(s)) + s.encode('utf_16_be')


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


def is_set_to_default(obj):
    traits = obj.traits()
    for key, val in traits.items():
        if getattr(obj, key) != val.default_value:
            return False
    return True


def ensure_bigendian(arr):
    order = arr.dtype.byteorder
    if order == '=':
        if sys.byteorder == 'little':
            order = '<'
        else:
            order = '>'

    if order != '>':
        return arr.byteswap().view(arr.dtype.newbyteorder('>'))

    return arr
