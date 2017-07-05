cimport cpython
from cpython.buffer cimport (
    Py_buffer, PyObject_GetBuffer, PyBuffer_Release, PyBUF_C_CONTIGUOUS)
from libc.stdint cimport uint16_t, uint32_t, uint64_t
cimport cython


import sys


@cython.boundscheck(False)
def decode_prediction_8bit(data):
    cdef unsigned char [:] input = data
    cdef int i

    for i in range(input.shape[0] - 1):
        input[i+1] += input[i]


@cython.boundscheck(False)
def decode_prediction_16bit(data):
    cdef unsigned short [:] input = data

    cdef int i

    for i in range(input.shape[0] - 1):
        input[i+1] += input[i]


@cython.boundscheck(False)
def encode_prediction_8bit(data):
    cdef unsigned char [:] input = data

    cdef int i

    for i in range(input.shape[0] - 1, 0, -1):
        input[i] -= input[i-1]


@cython.boundscheck(False)
def encode_prediction_16bit(data):
    cdef unsigned short [:] input = data

    cdef int i

    for i in range(input.shape[0] - 1, 0, -1):
        input[i] -= input[i-1]


@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline void decode_row(unsigned char *input,
                            size_t length,
                            unsigned char *output):
    cdef char header_byte
    cdef size_t input_pos = 0
    cdef size_t output_pos = 0
    while input_pos < length:
        header_byte = <char>input[input_pos]
        input_pos += 1

        if 0 <= header_byte:
            for i in range(header_byte + 1):
                output[output_pos] = input[input_pos]
                output_pos += 1
                input_pos += 1
        elif header_byte != -128:
            for j in range(1 - header_byte):
                output[output_pos] = input[input_pos]
                output_pos += 1
            input_pos += 1


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.overflowcheck(False)
def decode(data, size_t height, size_t width, size_t depth, int version):
    """
    Decodes PackBit encoded data.
    """
    cdef int need_swap = (sys.byteorder == 'little')

    cdef unsigned char *input
    cdef Py_ssize_t input_size
    cpython.PyBytes_AsStringAndSize(data, <char **>&input, &input_size)

    output_obj = cpython.PyBytes_FromStringAndSize(NULL, height * width * depth)
    cdef unsigned char *output
    cdef Py_ssize_t output_size
    cpython.PyBytes_AsStringAndSize(output_obj, <char **>&output, &output_size)

    cdef uint16_t *lengths_u16 = <uint16_t *>input
    cdef uint32_t *lengths_u32 = <uint32_t *>input
    cdef uint64_t length
    cdef size_t i

    if version == 1:
        input = &input[2 * height]
        for i in range(height):
            length = lengths_u16[i]
            if need_swap:
                length = ((length & 0xff) << 8) | ((length & 0xff00) >> 8)
            decode_row(input, length, &output[i * width * depth])
            input = &input[length]
    else:
        input = &input[4 * height]
        for i in range(height):
            length = lengths_u32[i]
            if need_swap:
                length = (((length & <uint64_t>0xff000000) >> 24) |
                          ((length & <uint64_t>0xff00) << 8) |
                          ((length & <uint64_t>0xff0000) >> 8) |
                          ((length & <uint64_t>0xff) << 24))
            decode_row(input, length, &output[i * width * depth])
            input = &input[length]

    return output_obj


@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline void finish_raw(unsigned char *buffer, int buffer_pos,
                            unsigned char *output, int *output_pos):
    cdef int i

    if buffer_pos == 0:
        return
    output[output_pos[0]] = buffer_pos - 1
    output_pos[0] += 1
    for i in range(buffer_pos):
        output[output_pos[0]] = buffer[i]
        output_pos[0] += 1


@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline void finish_rle(unsigned char *input, int input_pos,
                            unsigned char *output, int output_pos,
                            int repeat_count):
    output[output_pos] = 256 - (repeat_count - 1)
    output[output_pos + 1] = input[input_pos]


@cython.boundscheck(False)
@cython.wraparound(False)
def encode(data):
    """
    Encodes PackBit encoded data.
    """
    cdef Py_buffer buff
    if PyObject_GetBuffer(
            data, &buff, PyBUF_C_CONTIGUOUS):
        raise ValueError("Couldn't get buffer")

    if buff.len == 0:
        PyBuffer_Release(&buff)
        return b''

    if buff.len == 1:
        PyBuffer_Release(&buff)
        return b'\x00' + data.tobytes()

    cdef unsigned char *input = <unsigned char *>buff.buf
    cdef Py_ssize_t input_size = buff.len

    output_obj = cpython.PyBytes_FromStringAndSize(NULL, input_size * 2)
    cdef unsigned char *output
    cdef Py_ssize_t output_size
    cpython.PyBytes_AsStringAndSize(output_obj, <char **>&output, &output_size)

    cdef unsigned char buffer[256]

    cdef int input_pos, output_pos, buffer_pos
    cdef int state  # RAW = 0, RLE = 1
    cdef int repeat_count
    cdef unsigned char current_byte

    input_pos = 0
    output_pos = 0
    buffer_pos = 0
    repeat_count = 0
    state = 0

    while input_pos < input_size - 1:
        current_byte = input[input_pos]

        if current_byte == input[input_pos + 1]:
            if state:
                if repeat_count == 127:
                    finish_rle(
                        input, input_pos, output, output_pos, repeat_count)
                    output_pos += 2
                    repeat_count = 0
                repeat_count += 1
            else:
                finish_raw(buffer, buffer_pos, output, &output_pos)
                buffer_pos = 0
                state = 1
                repeat_count = 1
        else:
            if state:
                repeat_count += 1
                finish_rle(
                    input, input_pos, output, output_pos, repeat_count)
                output_pos += 2
                state = 0
                repeat_count = 0
            else:
                if buffer_pos == 127:
                    finish_raw(buffer, buffer_pos, output, &output_pos)
                    buffer_pos = 0
                buffer[buffer_pos] = current_byte
                buffer_pos += 1

        input_pos += 1

    if state:
        repeat_count += 1
        finish_rle(
            input, input_pos, output, output_pos, repeat_count)
        output_pos += 2
    else:
        buffer[buffer_pos] = input[input_pos]
        buffer_pos += 1
        finish_raw(buffer, buffer_pos, output, &output_pos)

    PyBuffer_Release(&buff)

    return output_obj[:output_pos]
