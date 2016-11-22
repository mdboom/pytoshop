===============================
pytoshop
===============================


.. image:: https://img.shields.io/pypi/v/pytoshop.svg
        :target: https://pypi.python.org/pypi/pytoshop

.. image:: https://img.shields.io/travis/mdboom/pytoshop.svg
        :target: https://travis-ci.org/mdboom/pytoshop

.. image:: https://readthedocs.org/projects/pytoshop/badge/?version=latest
        :target: https://pytoshop.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://img.shields.io/codecov/c/github/mdboom/pytoshop.svg
        :target: https://codecov.io/gh/mdboom/pytoshop
        :alt: Coverage status


A Python-based library to read and write Photoshop PSD and PSB files.

Based on the specification `from Adobe
<https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/>`__,
but also with the help of the `psd-tools
<https://github.com/psd-tools/psd-tools/>`__ source code.


* Free software: BSD license
* Documentation: https://pytoshop.readthedocs.io.


Features
--------

- Parsing of the most important tags.  This is not complete, but the
  infrastructure is in place to add support for more quite easily.

- Loading of complex nested layer structures, and the ability to edit
  them and write them back out.
