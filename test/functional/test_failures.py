import subprocess
import functools
import tempfile
import logging
import select
import os

try:
    # python 3
    from io import BytesIO
except ImportError:
    # python 2
    import StringIO.StringIO as BytesIO

from .accessories import (
    # recv_prog,
    send_prog,
    fill_binary_data,
    verify_binary_data,
)
from xmodem import XMODEM, XMODEM1k

logging.basicConfig(format='%(levelname)-5s %(message)s',
                    level=logging.DEBUG)


CHECKFAIL_SEQ = 0


def _proc_getc_fail_16bit_checksum(size, timeout=1, proc=None, num_failures=1):
    # this getc function adjusts the final checksum of the first block to be
    # failed, causing a purge and retransmission of the first block.
    global CHECKFAIL_SEQ
    assert proc.returncode is None, ("{0} has exited: (returncode={1})"
                                     .format(proc, proc.returncode))
    logging.debug(('get', size))
    ready_read, _, _ = select.select([proc.stdout], [], [], timeout)
    if proc.stdout not in ready_read:
        return None
    data = proc.stdout.read(size)
    if len(data) == 130 and CHECKFAIL_SEQ < num_failures:
        CHECKFAIL_SEQ += 1
        _checksum = bytearray(data[-2:])
        _checksum[0] |= 0xb0
        _checksum[1] |= 0x0b
        data = bytearray(data[:-2]) + _checksum
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
    if not ready_write:
        assert False, ("Timeout on stdin of {0}.".format(proc))
    logging.debug(('put', len(data), data))
    proc.stdin.write(data)
    proc.stdin.flush()
    return len(data)


def test_xmodem_recv_bad_checksum():
    """
    Using external program for send, verify checksum fail in XMODEM.recv().
    """
    # Given,
    _, send_filename = tempfile.mkstemp()
    try:
        with open(send_filename, 'wb') as stream:
            fill_binary_data(stream)
        proc = subprocess.Popen(
            (send_prog, '--xmodem', '--verbose', send_filename),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

        getc = functools.partial(_proc_getc_fail_16bit_checksum, proc=proc)
        putc = functools.partial(_proc_putc, proc=proc)

        xmodem = XMODEM(getc, putc)
        recv_stream = BytesIO()

        # Exercise,
        status = xmodem.recv(recv_stream, timeout=5, crc_mode=1)

        # Verify,
        assert status == recv_stream.tell()
        verify_binary_data(recv_stream, padding=b'\x1a')
        proc.wait()
        assert proc.returncode == 0

    finally:
        os.unlink(send_filename)


def test_xmodem1k_recv_bad_checksum():
    """
    Using external program for send, verify checksum fail in XMODEM.recv().
    """
    # Given,
    _, send_filename = tempfile.mkstemp()
    try:
        with open(send_filename, 'wb') as stream:
            fill_binary_data(stream)
        proc = subprocess.Popen(
            (send_prog, '--xmodem', '--verbose', send_filename),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

        getc = functools.partial(_proc_getc_fail_16bit_checksum, proc=proc)
        putc = functools.partial(_proc_putc, proc=proc)

        xmodem = XMODEM1k(getc, putc)
        recv_stream = BytesIO()

        # Exercise,
        status = xmodem.recv(recv_stream, timeout=5, crc_mode=1)

        # Verify,
        assert status == recv_stream.tell()
        verify_binary_data(recv_stream, padding=b'\x1a')
        proc.wait()
        assert proc.returncode == 0

    finally:
        os.unlink(send_filename)
