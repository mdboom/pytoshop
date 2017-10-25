# -*- coding: utf-8 -*-


import pytest


from pytoshop import blending_range


def _test_default_blending_range(b):
    assert b.black0 == 0
    assert b.black1 == 0
    assert b.white0 == 0
    assert b.white1 == 0


def test_default_blending_range():
    b = blending_range.BlendingRange()

    _test_default_blending_range(b)

    b.black0 = 1
    b.black1 = 2
    b.white0 = 3
    b.white1 = 4

    assert b.black0 == 1
    assert b.black1 == 2
    assert b.white0 == 3
    assert b.white1 == 4


def test_default_blending_range_pair():
    pair = blending_range.BlendingRangePair()

    _test_default_blending_range(pair.src)
    _test_default_blending_range(pair.dst)

    with pytest.raises(TypeError):
        pair.src = None

    with pytest.raises(TypeError):
        pair.dst = None

    pair.src = pair.dst
