# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


import glob
import io
import os


import pytest


import psdwriter


path = os.path.join(os.path.dirname(__file__), 'psd_files', '*.psd')


@pytest.mark.parametrize("filename", glob.glob(path))
def test_files(filename):
    print(filename)
    with open(filename, 'rb') as fd:
        f = psdwriter.PsdFile.read(fd)

    fd = io.BytesIO()
    f.write(fd)
