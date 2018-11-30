=======
History
=======

1.2.1 (2018-11-30) (2017-12-13) (2017-09-26)
------

Bugfixes:

- Fix #4: Change masked layer to same size as image layer when using
  the `user.nested_layers` interface.

1.0.1 (2017-08-01) (2017-07-29)
------

- Declared API as stable.

0.6.0 (2017-07-24)
------

Minor improvements:

- Make it easier to choose the right channel, given the current color
  mode.

0.5.0 (2017-07-03)
------

Minor improvements:

- The color assigned to a layer (displayed in the layer list) is now
  available in the ``nested_layers`` API.

Bugfixes:

- Fix crash in ``GuideResourceBlock``.

0.4.1 (2017-06-05)
------------------

Minor improvements:

- Parse multiple values in a struct together when possible.  This has
  a modest speed improvement.

Bugfixes:

- Fix pip install [#1]

- The main canvas image will use the specified compression algorithm
  when using nested_layers_to_psd.

- Non-image layers correctly set "pixel_data_is_irrelevant" flag.

0.4.0 (2017-05-12)
------------------

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

0.3.0 (2017-01-09)
------------------

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
