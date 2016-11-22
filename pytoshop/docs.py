# -*- coding: utf-8 -*-

"""
Documentation snippets.
"""

from __future__ import unicode_literals, absolute_import


read_single = """
Instantiate from a file-like object.

Parameters
----------
fd : file-like object
    Must be readable, seekable and open in binary mode.
"""


read = read_single + """
header : PsdFile object
    An object to get global file information from.
"""


write_single = """
Write to a file-like object.

Parameters
----------
fd : file-like object
    Must be writable, seekable and open in binary mode.
"""


write = write_single + """
header : PsdFile object
    An object to get global file information from.
"""


length = """
The length of the section, in bytes, not including its header.
"""


total_length = """
The length of the section, in bytes, including its header.
"""
