#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'cython',
    'numpy',
    'traitlets'
]

test_requirements = [
    'pytest'
]


extensions = [
    Extension(
        "psdwriter.packbits",
        ["psdwriter/packbits.pyx"]
    )
]

setup(
    name='psdwriter',
    version='0.1.0',
    description="A Python-based library to write Photoshop PSD files",
    long_description=readme + '\n\n' + history,
    author="Michael Droettboom",
    author_email='mdboom@gmail.com',
    url='https://github.com/mdboom/psdwriter',
    packages=[
        'psdwriter',
        'psdwriter.user'
    ],
    package_dir={'psdwriter':
                 'psdwriter'},
    include_package_data=True,
    install_requires=requirements,
    license="BSD license",
    zip_safe=False,
    keywords='psdwriter',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    ext_modules=cythonize(extensions)
)
