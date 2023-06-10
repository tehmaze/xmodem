# std imports
from __future__ import print_function
import os
import sys
import select
import logging
import tempfile
import functools
import subprocess

import pytest

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

MISSING_LRB_MSG = "'rb' or 'lrb' required. Try installing the 'lrzsz' package"
MISSING_LSB_MSG = "'sb' or 'lsb' required. Try installing the 'lrzsz' package"

def _proc_getc(size, timeout=1, proc=None):
    # our getc function pipes to the standard out of the `rb'
    # or `lrb' program -- any data written by 'rb' is returned
    # by our getc() callback.
    assert proc.returncode is None, ("{0} has exited: (returncode={1})"
                                     .format(proc, proc.returncode))
    logging.debug('_proc_getc: read (size=%s, timeout=%s)', size, timeout)
    ready_read, _, _ = select.select([proc.stdout], [], [], timeout)
    if proc.stdout not in ready_read:
        assert False, ("Timeout on stdout of {0}.".format(proc))
    data = proc.stdout.read(size)
    logging.debug('_proc_getc: read %s bytes: %r', len(data), data)
    return data


def _proc_putc(data, timeout=1, proc=None):
    # similarly, the putc function pipes to standard in of the 'rb'
    # or `lrb' program -- any data written by our XMODEM
    # protocol via putc() callback is written to the stdin 'rb'.
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
    # this callback asserts that no errors have occurred, and
    # prints the given status to stderr.  This is captured but displayed in
    # py.test output only on error.
    assert error_count == 0
    assert success_count == total_packets
    logging.debug('_send_callback: total_packets=%s, success_count=%s, error_count=%s',
                  total_packets, success_count, error_count)


@pytest.mark.skipif(recv_prog is None, reason=MISSING_LRB_MSG)
def test_xmodem_send_with_lrb():
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


@pytest.mark.skipif(send_prog is None, reason=MISSING_LSB_MSG)
def test_xmodem_recv_with_lsb():
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


@pytest.mark.skipif(recv_prog is None, reason=MISSING_LRB_MSG)
def test_xmodem1k_send_with_lrb():
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


@pytest.mark.skipif(send_prog is None, reason=MISSING_LSB_MSG)
def test_xmodem1k_recv_with_lsb():
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


@pytest.mark.skipif(recv_prog is None, reason=MISSING_LRB_MSG)
def test_xmodem_send_16bit_crc_with_lrb():
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


def test_xmodem_recv_oldstyle_checksum_with_lrb():
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
