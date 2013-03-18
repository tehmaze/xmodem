================================
 XMODEM protocol implementation
================================

Documentation available at http://packages.python.org/xmodem/

Source is available at ?

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

TODO
====

Here are some of the things that I want to do:

#. Automate the existing unit tests and push it into Jenkins.  Look at ways to make a probationary tag.  If the tag passes, finalize the tag and commit it.
#. Add more extensive unit tests.
#. Write the receive code to handle 1K XMODEM downloads.
#. Implement YMODEM or ZMODEM?
#. Clean up the API to make it a little easier to use.
#. Add callbacks to the receive method.
#. Are there any statistics that we should add to the callbacks, or should we force the user to build them?
#. Add a helper module for calculating statistics, sending/receiving files, printing status messages, sending qt signals, basic getc and putc implementations, etc.
#. Add an API for spinning out an upload or download as a thread or process (preferrably as a 1-liner for a basic implementation by the end user)

.. _documentation: http://packages.python.org/xmodem/xmodem.html
