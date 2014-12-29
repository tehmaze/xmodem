"""
Unit tests for XMODEM protocol.
"""
# std imports
try:
    # python 3
    from io import BytesIO
except ImportError:
    # python 2
    import StringIO.StringIO as BytesIO

# local
import xmodem

# 3rd-party
import pytest


def dummy_getc(size, timeout=1):
    return None


def dummy_putc(data, timeout=1):
    return 0


@pytest.mark.parametrize('mode', ['xmodem', 'xmodem1k'])
def test_xmodem_dummy_fails_send(mode):
    # given,
    modem = xmodem.XMODEM(getc=dummy_getc,
                          putc=dummy_putc,
                          mode=mode)
    # exercise
    status = modem.send(BytesIO(b'dummy-stream'))
    # verify
    assert not status, ("Expected value of status `False'")


def test_xmodem_bad_mode():
    # given,
    mode = 'XXX'
    modem = xmodem.XMODEM(getc=dummy_getc,
                          putc=dummy_putc,
                          mode=mode)
    # exercise
    with pytest.raises(ValueError):
        status = modem.send(BytesIO(b'dummy-stream'))
