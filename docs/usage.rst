=====
Usage
=====

To read a file and write it back out again::

    import pytoshop

    with open('image.psd', 'rb') as fd:
        psd = pytoshop.read(fd)

        with open('updated.psd', 'wb') as fd:
            psd.write(fd)

See the :ref:`api` documentation for more details.
