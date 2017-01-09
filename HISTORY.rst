=======
History
=======

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
