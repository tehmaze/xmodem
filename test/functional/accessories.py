import subprocess


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
