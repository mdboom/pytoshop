#!/usr/bin/env python
# -*- coding: utf-8 -*-


import io


import pytest


from pytoshop import core
from pytoshop import enums


class TestHeader(object):
    def test_header(self):
        content = b'8BPS\0\x02\0\0\0\0\0\0\0\x03\0\0\0\x0F\0\0\0\x0F\0\x08\0\1'
        fd = io.BytesIO(content)
        fd.seek(0)
        h = core.Header.header_read(fd)

        assert h.version == 2
        assert h.num_channels == 3
        assert h.height == 15
        assert h.width == 15
        assert h.depth == 8
        assert h.color_mode == enums.ColorMode.grayscale

        fd = io.BytesIO()
        h.write(fd)
        assert fd.getvalue() == content

    def test_header_invalid_version(self):
        content = b'8BPS\0\x03\0\0\0\0\0\0\0\x03\0\0\0\x0F\0\0\0\x0F\0\x08\0\1'
        fd = io.BytesIO(content)
        fd.seek(0)
        with pytest.raises(ValueError):
            core.Header.header_read(fd)

    def test_header_invalid_signature(self):
        content = b'8BPX\0\x02\0\0\0\0\0\0\0\x03\0\0\0\x0F\0\0\0\x0F\0\x08\0\1'
        fd = io.BytesIO(content)
        fd.seek(0)
        with pytest.raises(ValueError):
            core.Header.header_read(fd)

    def test_header_invalid_width(self):
        content = b'8BPS\0\x02\0\0\0\0\0\0\0\x03\0\0\0\0\0\0\0\x0F\0\x08\0\1'
        fd = io.BytesIO(content)
        fd.seek(0)
        with pytest.raises(ValueError):
            core.Header.header_read(fd)

    def test_header_invalid_depth(self):
        content = b'8BPS\0\x02\0\0\0\0\0\0\0\x03\0\0\0\x0F\0\0\0\x0F\0\x09\0\1'
        fd = io.BytesIO(content)
        fd.seek(0)
        with pytest.raises(ValueError):
            core.Header.header_read(fd)

    def test_size_too_large(self):
        with pytest.raises(ValueError):
            core.Header(version=1, width=30001, height=5)
        core.Header(version=2, width=30001, height=5)

        with pytest.raises(ValueError):
            core.Header(version=2, width=300001, height=5)

        with pytest.raises(ValueError):
            core.Header(version=1, width=5, height=30001)
        core.Header(version=2, width=5, height=30001)

        with pytest.raises(ValueError):
            core.Header(version=2, width=5, height=300001)
