================================
 XMODEM protocol implementation
================================

Documentation available at http://packages.python.org/xmodem/

Python Package Index (PyPI) page is available at https://pypi.python.org/pypi/xmodem

Usage
=====

Create a function to get and put character data (to a serial line for
example)::

    >>> from xmodem import XMODEM
    >>> def getc(size, timeout=1):
    ...     return data or None
    ...
    >>> def putc(data, timeout=1):
    ...     return size or None
    ...
    >>> modem = XMODEM(getc, putc)

Now, to upload a file, use the ``send`` method::

    >>> stream = open('/etc/fstab', 'rb')
    >>> modem.send(stream)

To download a file, use the ``recv`` method::

    >>> stream = open('output', 'wb')
    >>> modem.recv(stream)

For more information, take a look at the documentation_.

.. _documentation: http://packages.python.org/xmodem/xmodem.html

.. image:: https://travis-ci.org/tehmaze/xmodem.png?branch=master
   :target: https://travis-ci.org/tehmaze/xmodem

.. image:: https://coveralls.io/repos/tehmaze/xmodem/badge.png
   :target: https://coveralls.io/r/tehmaze/xmodem
