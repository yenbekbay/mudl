mudl - music downloader
----------------------------------

.. image:: https://img.shields.io/pypi/v/mudl.svg
    :target: https://pypi.python.org/pypi/mudl

.. image:: https://img.shields.io/pypi/dw/mudl.svg
    :target: https://pypi.python.org/pypi/mudl

.. image:: https://img.shields.io/pypi/l/mudl.svg
    :target: https://raw.githubusercontent.com/yenbekbay/mudl/master/LICENSE

A cli tool for downloading music from VK in high quality and with correct tags and a cover art. Works best for electronic music.

Supports both Python 2.x and 3.x

.. image:: https://raw.githubusercontent.com/yenbekbay/mudl/master/demo.gif

Installation
------------

You need to have pip installed https://pip.pypa.io/en/latest/installing.html.

To install from PyPI, run the following command:

.. code-block:: shell

  $ pip install mudl

For usage, run ``mudl -h`` or ``mudl --help``.

Usage
-----

.. code-block:: shell

    mudl [-h] [-q {high,medium,low}] [--skipmatch] [--configure] [query]

    Downloads the mp3 file for the given query if the track can be found on VK in
    the given quality
    
    positional arguments:
      query                 The track title to look for (Artist - Title)
    
    optional arguments:
      -h, --help            show this help message and exit
      -q {high,medium,low}, --quality {high,medium,low}
                            minimum quality for the downloaded track, where high =
                            320kbps, medium = 256kbps, and low = 128kbps (default
                            is high)
      --skipmatch           skip matching for track (decreases accuracy)
      --configure           edit the configuration

The MIT License
---------------

Copyright (C) 2015  Ayan Yenbekbay

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
