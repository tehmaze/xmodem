.. image:: https://travis-ci.org/tehmaze/xmodem.png?branch=master
   :target: https://travis-ci.org/tehmaze/xmodem

.. image:: https://coveralls.io/repos/tehmaze/xmodem/badge.png
   :target: https://coveralls.io/r/tehmaze/xmodem

================================
 XMODEM protocol implementation
================================

Documentation available at http://packages.python.org/xmodem/

Python Package Index (PyPI) page is available at https://pypi.python.org/pypi/xmodem

Usage
=====

Create a function to get and put character data (to a serial line for
example)::

    >>> import serial
    >>> from xmodem import XMODEM
    >>> ser = serial.Serial('/dev/ttyUSB0', timeout=0) # or whatever port you need
    >>> def getc(size, timeout=1):
    ...     return ser.read(size) or None
    ...
    >>> def putc(data, timeout=1):
    ...     return ser.write(data)  # note that this ignores the timeout
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

Changes
=======

0.4.6:
  * bugfix: Abort send on EOT in startup-sequence `Issue #34 
    <https://github.com/tehmaze/xmodem/issues/34>`_.
  * enhancement: Include LICENSE file in the source distribution.

0.4.5:
  * bugfix: Remove bogus `assert False` code in ``recv()`` that resulted in
    `AssertionError` introduced in version 0.4.0 commit-id `9b03fc20`, `PR #29
    <https://github.com/tehmaze/xmodem/pull/29>`_.

0.4.4:
  * bugfix: Large file transfers in ``send()`` were more likely to fail for
    small values of ``retry``: This value should be the maximum failures per
    block transfer as documented, but was improperly implemented as the number
    of failures allowed for the total duration of the transfer, `PR #21
    <https://github.com/tehmaze/xmodem/pull/21>`_.
  * bugfix: ``send(retry=n)`` and ``recv(retry=n)`` should retry ``n`` times
    as documented, was retrying ``n - 1``.

0.4.3:
  * bugfix: ``putc()`` callback was called in series, 3 times for each part of
    xmodem block header, data, and checksum during block transfer.  Now all
    three data blocks are sent by single ``putc()`` call.  This resolves issues
    when integrating with microcontrollers or equipment sensitive to timing
    issues at stream boundaries, `PR #19
    <https://github.com/tehmaze/xmodem/pull/19>`_.

0.4.2:
  * bugfix: documentation files missing from the release tarball
    `Issue #16 <https://github.com/tehmaze/xmodem/issues/16>`_.

0.4.1
  * bugfix: re-transmit in ``send()`` on ``NAK`` or timeout, previously
    re-transmissions (wrongly) occurred only on garbage bytes.
    `PR #12 <https://github.com/tehmaze/xmodem/pull/12>`_.

0.4.0
  * enhancement: support for python 3
    `PR #8 <https://github.com/tehmaze/xmodem/pull/8>`_.
  * bugfix: CRC failures in XMODEM.recv() were not renegotiated correctly
    `PR #11 <https://github.com/tehmaze/xmodem/issues/11>`_.
