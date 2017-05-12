=======
History
=======

0.4.0
-----

Improvements:

- For speed purposes, pytoshop no longer uses traitlets.

- Performance improvements to the compression/decompression code.

- Added support for the ``shmd`` metadata tagged block, and the ability
  to access it from the ``user.nested_layers`` API.

Bugfixes:

- Updated the list of tagged blocks that use 8-bit lengths.

- Fixed a bug where the image data would be corrupted when writing
  images from an input file to an output file with a different file
  format version.

- Fixed a crash when the input file contains no layer group ids.

- Allow Numpy arrays of shape () in place of scalars for constant
  images.

0.3.0
-----

Improvements:

- ``pytoshop`` now runs on Python 2.7, in addition to 3.4 and 3.5.

- Many of the image resources types are now handled directly, rather
  than through a generic bytes-only interface.

- Major speedups in compression codecs.

Bugfixes:

- Saving a layer with a constant color (in ``nested_layers_to_psd``)
  now works correctly.

- Unicode string decoding now properly handles trailing zeroes.

- The "name source" on layers (when created from
  ``nested_layers_to_psd``) would point to the wrong source, but is
  now fixed.

- Fix a bug when writing a layer of width 1.
