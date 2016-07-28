# -*- coding: utf-8 -*-


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
