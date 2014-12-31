import subprocess
import errno


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

CHUNKSIZE = 521


def fill_binary_data(stream):
    for byte in range(0x00, 0xff + 1, 10):
        stream.write(bytearray([byte] * CHUNKSIZE))
    stream.seek(0)
    return stream


def verify_binary_data(stream, padding):
    stream.seek(0)
    for byte in range(0x00, 0xff + 1, 10):
        assert stream.read(CHUNKSIZE) == bytearray([byte] * CHUNKSIZE)
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
