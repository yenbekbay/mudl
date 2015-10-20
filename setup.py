#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of mudl.
# Copyright (C) 2015 Ayan Yenbekbay
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

from setuptools import setup
from codecs import open # pylint: disable=redefined-builtin
from os import path

def _read(fn):
    return open(path.join(path.dirname(__file__), fn)).read()

setup(
    name='mudl',
    version='0.1.0',
    description='A cli tool for downloading music from VK in high quality',
    long_description=_read('README.rst'),
    url='https://github.com/yenbekbay/mudl',
    author='Ayan Yenbekbay',
    author_email='ayan.yenb@gmail.com',
    license='MIT',
    classifiers=[
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Sound/Audio',
    ],
    keywords='music downloader mp3',
    install_requires=[
        'soundcloud>=0.4.1',
        'musicbrainzngs>=0.5',
        'mutagen>=1.27',
        'clint>=0.3.4',
        'future>=0.15.2',
        'furl>=0.4.8'
    ],
    extras_require={},
    packages=['mudl'],
    entry_points={
        'console_scripts': [
            'mudl = mudl:main',
        ],
    }
)
