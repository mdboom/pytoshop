# -*- coding: utf-8 -*-


import io
import os


import psdwriter
from psdwriter.user import nested_layers


DATA_PATH = os.path.join(os.path.dirname(__file__), 'psd_files')


def test_nested_layers():
    filename = os.path.join(DATA_PATH, 'group.psd')
    with open(filename, 'rb') as fd:
        psd = psdwriter.PsdFile.read(fd)

    layers = nested_layers.psd_to_nested_layers(psd)

    psd2 = nested_layers.nested_layers_to_psd(layers)

    fd = io.BytesIO()
    psd2.write(fd)


def test_nested_layers_no_adjust():
    filename = os.path.join(DATA_PATH, 'group.psd')
    with open(filename, 'rb') as fd:
        psd = psdwriter.PsdFile.read(fd)

    layers = nested_layers.psd_to_nested_layers(psd)

    psd2 = nested_layers.nested_layers_to_psd(
        layers, size=(psd.header.width, psd.header.height))

    fd = io.BytesIO()
    psd2.write(fd)
