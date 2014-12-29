# std imports
from __future__ import print_function
import os
import sys
import select
import logging
import tempfile
import functools
import subprocess
try:
    # python 3
    from io import BytesIO
except ImportError:
    # python 2
    import StringIO.StringIO as BytesIO

# local
from xmodem import XMODEM, XMODEM1k
from .accessories import (
    recv_prog,
    send_prog,
    fill_binary_data,
    verify_binary_data,
)

logging.basicConfig(format='%(levelname)-5s %(message)s',
                    level=logging.DEBUG)


def _proc_getc(size, timeout=1, proc=None):
    # our getc function simply pipes to the standard out of the `rb'
    # or `lrb' program -- any data written by such program is returned
    # by our getc() callback.
    assert proc.returncode is None, ("{0} has exited: (returncode={1})"
                                     .format(proc, proc.returncode))
    logging.debug(('get', size))
    ready_read, _, _ = select.select([proc.stdout], [], [], timeout)
    if proc.stdout not in ready_read:
        assert False, ("Timeout on stdout of {0}.".format(proc))
    data = proc.stdout.read(size)
    logging.debug(('got', len(data), data))
    return data


def _proc_putc(data, timeout=1, proc=None):
    # similarly, our putc function simply writes to the standard of
    # our `rb' or `lrb' program -- any data written by our XMODEM
    # protocol via putc() callback is written to the stdin of such
    # program.
    assert proc.returncode is None, ("{0} has exited: (returncode={1})"
                                     .format(proc, proc.returncode))
    _, ready_write, _ = select.select([], [proc.stdin], [], timeout)
    if proc.stdin not in ready_write:
        assert False, ("Timeout on stdin of {0}.".format(proc))
    logging.debug(('put', len(data), data))
    proc.stdin.write(data)
    proc.stdin.flush()
    return len(data)


def _send_callback(total_packets, success_count, error_count):
    # this simple callback simply asserts that no errors have occurred, and
    # prints the given status to stderr.  This is captured but displayed in
    # py.test output only on error.
    assert error_count == 0
    assert success_count == total_packets
    print('{0}'.format(total_packets), file=sys.stderr)


def test_xmodem_send():
    """ Using external program for receive, verify XMODEM.send(). """
    # Given,
    _, recv_filename = tempfile.mkstemp()
    try:
        proc = subprocess.Popen(
            (recv_prog, '--xmodem', '--verbose', recv_filename),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

        getc = functools.partial(_proc_getc, proc=proc)
        putc = functools.partial(_proc_putc, proc=proc)

        xmodem = XMODEM(getc, putc, pad=b'\xbb')
        stream = fill_binary_data(BytesIO())

        # Exercise,
        status = xmodem.send(stream, timeout=5, callback=_send_callback)

        # Verify,
        assert status is True
        verify_binary_data(stream, padding=b'\xbb')
        verify_binary_data(open(recv_filename, 'rb'), padding=b'\xbb')
        proc.wait()
        assert proc.returncode == 0

    finally:
        if os.path.isfile(recv_filename):
            os.unlink(recv_filename)


def test_xmodem_recv():
    """ Using external program for send, verify XMODEM.recv(). """
    # Given,
    _, send_filename = tempfile.mkstemp()
    try:
        with open(send_filename, 'wb') as stream:
            fill_binary_data(stream)
        proc = subprocess.Popen(
            (send_prog, '--xmodem', '--verbose', send_filename),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

        getc = functools.partial(_proc_getc, proc=proc)
        putc = functools.partial(_proc_putc, proc=proc)

        xmodem = XMODEM(getc, putc)
        recv_stream = BytesIO()

        # Exercise,
        status = xmodem.recv(recv_stream, timeout=5)

        # Verify,
        assert status == recv_stream.tell()
        verify_binary_data(recv_stream, padding=b'\x1a')
        proc.wait()
        assert proc.returncode == 0

    finally:
        os.unlink(send_filename)


def test_xmodem1k_send():
    """ Using external program for receive, verify XMODEM1k.send(). """
    # Given,
    _, recv_filename = tempfile.mkstemp()
    try:
        proc = subprocess.Popen(
            (recv_prog, '--xmodem', '--verbose', recv_filename),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

        getc = functools.partial(_proc_getc, proc=proc)
        putc = functools.partial(_proc_putc, proc=proc)

        xmodem = XMODEM1k(getc, putc, pad=b'\xbb')
        stream = fill_binary_data(BytesIO())

        # Exercise,
        status = xmodem.send(stream, timeout=5, callback=_send_callback)

        # Verify,
        assert status is True
        verify_binary_data(stream, padding=b'\xbb')
        verify_binary_data(open(recv_filename, 'rb'), padding=b'\xbb')
        proc.wait()
        assert proc.returncode == 0

    finally:
        os.unlink(recv_filename)


def test_xmodem1k_recv():
    """ Using external program for send, verify XMODEM1k.recv(). """
    # Given,
    _, send_filename = tempfile.mkstemp()
    try:
        with open(send_filename, 'wb') as stream:
            fill_binary_data(stream)
        proc = subprocess.Popen(
            (send_prog, '--xmodem', '--verbose', '--1k', send_filename),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

        getc = functools.partial(_proc_getc, proc=proc)
        putc = functools.partial(_proc_putc, proc=proc)

        xmodem = XMODEM1k(getc, putc)
        recv_stream = BytesIO()

        # Exercise,
        status = xmodem.recv(recv_stream, timeout=5)

        # Verify,
        assert status == recv_stream.tell()
        verify_binary_data(recv_stream, padding=b'\x1a')
        proc.wait()
        assert proc.returncode == 0

    finally:
        if os.path.isfile(send_filename):
            os.unlink(send_filename)


def test_xmodem_send_16bit_crc():
    """
    Using external program for receive, verify XMODEM.send() with 16-bit CRC.
    """
    # Given,
    _, recv_filename = tempfile.mkstemp()
    try:
        proc = subprocess.Popen(
            (recv_prog, '--xmodem', '--verbose', '--with-crc', recv_filename),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

        getc = functools.partial(_proc_getc, proc=proc)
        putc = functools.partial(_proc_putc, proc=proc)

        xmodem = XMODEM(getc, putc, pad=b'\xbb')
        stream = fill_binary_data(BytesIO())

        # Exercise,
        status = xmodem.send(stream, timeout=5, callback=_send_callback)

        # Verify,
        assert status is True
        verify_binary_data(stream, padding=b'\xbb')
        verify_binary_data(open(recv_filename, 'rb'), padding=b'\xbb')
        proc.wait()
        assert proc.returncode == 0

    finally:
        if os.path.isfile(recv_filename):
            os.unlink(recv_filename)


def test_xmodem_recv_oldstyle_checksum():
    """
    Using external program for send, verify XMODEM.recv() with crc_mode 0.
    """
    # Given,
    _, send_filename = tempfile.mkstemp()
    try:
        with open(send_filename, 'wb') as stream:
            fill_binary_data(stream)
        proc = subprocess.Popen(
            (send_prog, '--xmodem', '--verbose', send_filename),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

        getc = functools.partial(_proc_getc, proc=proc)
        putc = functools.partial(_proc_putc, proc=proc)

        xmodem = XMODEM(getc, putc)
        recv_stream = BytesIO()

        # Exercise,
        status = xmodem.recv(recv_stream, timeout=5, crc_mode=0)

        # Verify,
        assert status == recv_stream.tell()
        verify_binary_data(recv_stream, padding=b'\x1a')
        proc.wait()
        assert proc.returncode == 0

    finally:
        os.unlink(send_filename)
