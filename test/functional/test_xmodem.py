import os
import errno
import select
import logging
import platform
import tempfile
import functools
import subprocess
try:
    # python 3
    from io import BytesIO
except ImportError:
    # python 2
    import StringIO.StringIO as BytesIO
from xmodem import XMODEM, XMODEM1k

logging.basicConfig(format='%(levelname)-5s %(message)s',
                    level=logging.DEBUG)


def _multi_which(prog_names):
    for prog_name in prog_names:
        proc = subprocess.Popen(('which', prog_name), stdout=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode == 0:
            return stdout.strip()
    return None


def _get_recv_program():
    bin_path = _multi_which(('rb', 'lrb'))
    assert bin_path is not None, (
        "program required: {0!r}.  "
        "Try installing lrzsz package.".format(bin_path))
    return bin_path


def _get_send_program():
    bin_path = _multi_which(('sb', 'lsb'))
    assert bin_path is not None, (
        "program required: {0!r}.  "
        "Try installing lrzsz package.".format(bin_path))
    return bin_path

recv_prog = _get_recv_program()
send_prog = _get_send_program()


def _fill_binary_data(stream):
    chunksize = 521
    for byte in range(0x00, 0xff + 1):
        stream.write(bytearray([byte] * chunksize))
    stream.seek(0)
    return stream


def _verify_binary_data(stream, padding=b'\xff'):
    stream.seek(0)
    chunksize = 521
    for byte in range(0x00, 0xff + 1):
        assert stream.read(chunksize) == bytearray([byte] * chunksize)
    while True:
        try:
            # BSD-style EOF
            data = stream.read(1)
            assert data in (b'', padding)
            if data == b'':
                # BSD-style EOF
                break
        except OSError as err:
            # Linux-style EOF
            assert err.errno == errno.EIO


def _proc_getc(size, timeout=1, proc=None):
    # our getc function simply pipes to the standard out of the `rb'
    # or `lrb' program -- any data written by such program is returned
    # by our getc() callback.
    assert proc.returncode is None, ("{0} has exited: (returncode={1})"
                                     .format(proc, proc.returncode))
    logging.debug(('get', size))
    ready_read, _, _ = select.select([proc.stdout], [], [], timeout)
    if not ready_read:
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
    if not ready_write:
        assert False, ("Timeout on stdin of {0}.".format(proc))
    logging.debug(('put', len(data), data))
    proc.stdin.write(data)
    proc.stdin.flush()
    return len(data)


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
        stream = _fill_binary_data(BytesIO())

        # Exercise,
        status = xmodem.send(stream, timeout=5)

        # Verify,
        assert status is True
        _verify_binary_data(stream)
        _verify_binary_data(open(recv_filename, 'rb'), padding=b'\xbb')
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
            _fill_binary_data(stream)
        proc = subprocess.Popen(
            (send_prog, '--xmodem', '--verbose', send_filename),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

        getc = functools.partial(_proc_getc, proc=proc)
        putc = functools.partial(_proc_putc, proc=proc)

        xmodem = XMODEM(getc, putc, pad=b'\xbb')
        recv_stream = BytesIO()

        # Exercise,
        status = xmodem.recv(recv_stream, timeout=5)

        # Verify,
        assert status == recv_stream.tell()
        _verify_binary_data(recv_stream, padding=b'\xbb')
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
        stream = _fill_binary_data(BytesIO())

        # Exercise,
        status = xmodem.send(stream, timeout=5)

        # Verify,
        assert status is True
        _verify_binary_data(stream)
        _verify_binary_data(open(recv_filename, 'rb'), padding=b'\xbb')
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
            _fill_binary_data(stream)
        proc = subprocess.Popen(
            (send_prog, '--xmodem', '--verbose', '--1k', send_filename),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

        getc = functools.partial(_proc_getc, proc=proc)
        putc = functools.partial(_proc_putc, proc=proc)

        xmodem = XMODEM1k(getc, putc, pad=b'\xbb')
        recv_stream = BytesIO()

        # Exercise,
        status = xmodem.recv(recv_stream, timeout=5)

        # Verify,
        assert status == recv_stream.tell()
        _verify_binary_data(recv_stream, padding=b'\xbb')
        proc.wait()
        assert proc.returncode == 0

    finally:
        if os.path.isfile(send_filename):
            os.unlink(send_filename)
