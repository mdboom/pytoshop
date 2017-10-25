# -*- coding: utf-8 -*-


import pytest


from pytoshop import image_resources


def test_image_resources():
    r = image_resources.ImageResourceBlock()

    r.name = b'ascii'

    with pytest.raises(ValueError):
        r.name = 25

    with pytest.raises(ValueError):
        r.name = u'X' * 320

    r = image_resources.GenericImageResourceBlock()

    with pytest.raises(ValueError):
        r.resource_id = (1 << 16) + 1

    with pytest.raises(ValueError):
        r.data = u'UNICODE DATA'

    r = image_resources.ImageResourceUnicodeString()

    with pytest.raises(TypeError):
        r.value = b'bytes'
