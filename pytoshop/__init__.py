# -*- coding: utf-8 -*-


from __future__ import unicode_literals, absolute_import


from .core import PsdFile


__author__ = 'Michael Droettboom'
__email__ = 'mdboom@gmail.com'
__version__ = '1.2.1'


from typing import BinaryIO  # NOQA


def read(fd):
    # type: (BinaryIO) -> PsdFile
    """
    Read a PSD file from a file-like object.

    Parameters
    ----------
    fd : file-like object
        Must be readable, seekable and open in binary mode.

    Returns
    -------
    psdfile : PsdFile
    """
    return PsdFile.read(fd)
