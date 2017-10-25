# -*- coding: utf-8 -*-


import pytest


from pytoshop import util


def test_assert_is_list_of():
    with pytest.raises(TypeError):
        util.assert_is_list_of((), int)

    with pytest.raises(TypeError):
        util.assert_is_list_of(['foo'], int)

    with pytest.raises(ValueError):
        util.assert_is_list_of([-1, 9], int, 0, 10)
