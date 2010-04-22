from setuptools import setup, find_packages

setup(
    name         = 'xmodem',
    version      = '0.2',
    author       = 'Wijnand Modderman',
    author_email = 'maze@pyth0n.org',
    description  = ('XMODEM protocol implementation.'),
    long_description = '''
================================
 XMODEM protocol implementation
================================

Documentation available at http://packages.python.org/xmodem/

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
    >>> x = XMODEM(getc, putc)

Now, to upload a file, use the ``send`` method::

    >>> stream = open('/etc/fstab', 'rb')
    >>> x.send(stream)

To download a file, use the ``recv`` method::

    >>> stream = open('output', 'wb')
    >>> x.recv(stream)

For more information, take a look at the documentation_.

.. _documentation: http://packages.python.org/xmodem/xmodem.html

''',
    license      = 'MIT',
    keywords     = 'xmodem protocol',
    packages     = ['xmodem'],
    package_data = {'': ['doc/*.TXT']},
)

