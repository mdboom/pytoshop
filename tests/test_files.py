# -*- coding: utf-8 -*-


import glob
import io
import os


import pytest


import pytoshop


path = os.path.join(os.path.dirname(__file__), 'psd_files', '*.psd')


@pytest.mark.parametrize("filename", glob.glob(path))
def test_files(filename):
    if filename.endswith('rt.psd'):
        return

    with open(filename, 'rb') as fd:
        f = pytoshop.read(fd)

        channels = f.image_data.channels
        assert channels is not None
        shape = f.image_data.shape
        assert len(shape) == 3
        info_map = f.layer_and_mask_info.additional_layer_info_map
        assert isinstance(info_map, dict)

        fd2 = io.BytesIO()
        f.write(fd2)

    fd2.seek(0)
    f = pytoshop.PsdFile.read(fd2)


@pytest.mark.parametrize("filename", glob.glob(path))
def test_convert_to_version2(filename):
    if filename.endswith('rt.psd'):
        return

    with open(filename, 'rb') as fd:
        f = pytoshop.read(fd)
        f.version = 2

        # Disable compression just to make these tests faster
        # for layer in f.layer_and_mask_info.layer_info.layer_records:
        #     for channel in layer.channels.values():
        #         channel.compression = 0

        fd2 = io.BytesIO()
        f.write(fd2)

    fd2.seek(0)
    f = pytoshop.PsdFile.read(fd2)
