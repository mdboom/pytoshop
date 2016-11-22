cimport cpython


def decode_prediction_8bit(data):
    cdef unsigned char [:] input = data
    cdef int i

    for i in range(input.shape[0] - 1):
        input[i+1] += input[i]


def decode_prediction_16bit(data):
    cdef unsigned short [:] input = data

    cdef int i

    for i in range(input.shape[0] - 1):
        input[i+1] += input[i]


def encode_prediction_8bit(data):
    cdef unsigned char [:] input = data

    cdef int i

    for i in range(input.shape[0] - 1, 0, -1):
        input[i] -= input[i-1]


def encode_prediction_16bit(data):
    cdef unsigned short [:] input = data

    cdef int i

    for i in range(input.shape[0] - 1, 0, -1):
        input[i] -= input[i-1]


def decode(data, size_t width):
    """
    Decodes PackBit encoded data.
    """
    cdef int input_pos, output_pos
    cdef int i
    cdef char header_byte

    cdef unsigned char *input
    cdef Py_ssize_t input_size
    cpython.PyBytes_AsStringAndSize(data, <char **>&input, &input_size)

    output_obj = cpython.PyBytes_FromStringAndSize(NULL, width)
    cdef unsigned char *output
    cdef Py_ssize_t output_size
    cpython.PyBytes_AsStringAndSize(output_obj, <char **>&output, &output_size)

    input_pos = 0
    output_pos = 0
    while input_pos < input_size:
        header_byte = <char>input[input_pos]
        input_pos += 1

        if 0 <= header_byte <= 127:
            for i in range(header_byte + 1):
                output[output_pos] = input[input_pos]
                output_pos += 1
                input_pos += 1
        elif header_byte != -128:
            for j in range(1 - header_byte):
                output[output_pos] = input[input_pos]
                output_pos += 1
            input_pos += 1

    return output_obj


cdef void finish_raw(unsigned char *buffer, int *buffer_pos,
                     unsigned char *output, int *output_pos):
    cdef int i

    if buffer_pos[0] == 0:
        return
    output[output_pos[0]] = buffer_pos[0] - 1
    output_pos[0] += 1
    for i in range(buffer_pos[0]):
        output[output_pos[0]] = buffer[i]
        output_pos[0] += 1
    buffer_pos[0] = 0


cdef void finish_rle(unsigned char *input, int *input_pos,
                     unsigned char *output, int *output_pos,
                     int repeat_count):
    output[output_pos[0]] = 256 - (repeat_count - 1)
    output_pos[0] += 1
    output[output_pos[0]] = input[input_pos[0]]
    output_pos[0] += 1


def encode(data):
    """
    Encodes PackBit encoded data.
    """
    if len(data) == 0:
        return data

    if len(data) == 1:
        return b'\x00' + data

    cdef unsigned char *input
    cdef Py_ssize_t input_size
    cpython.PyBytes_AsStringAndSize(data, <char **>&input, &input_size)

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
            if state == 0:
                finish_raw(buffer, &buffer_pos, output, &output_pos)
                state = 1
                repeat_count = 1
            elif state == 1:
                if repeat_count == 127:
                    finish_rle(
                        input, &input_pos, output, &output_pos, repeat_count)
                    repeat_count = 0
                repeat_count += 1
        else:
            if state == 0:
                if buffer_pos == 127:
                    finish_raw(buffer, &buffer_pos, output, &output_pos)
                buffer[buffer_pos] = current_byte
                buffer_pos += 1
            elif state == 1:
                repeat_count += 1
                finish_rle(
                    input, &input_pos, output, &output_pos, repeat_count)
                state = 0
                repeat_count = 0

        input_pos += 1

    if state == 0:
        buffer[buffer_pos] = input[input_pos]
        buffer_pos += 1
        finish_raw(buffer, &buffer_pos, output, &output_pos)
    else:
        repeat_count += 1
        finish_rle(
            input, &input_pos, output, &output_pos, repeat_count)

    return output_obj[:output_pos]
