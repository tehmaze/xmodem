"""
Unit tests for XMODEM protocol.
"""
# std imports
try:
    # python 3
    from io import BytesIO
except ImportError:
    # python 2
    from StringIO import StringIO as BytesIO

# local
from xmodem import NAK, CRC, ACK, XMODEM

# 3rd-party
import pytest


def dummy_getc(size, timeout=1):
    return None


def dummy_putc(data, timeout=1):
    return 0


def test_xmodem_bad_mode():
    # given,
    mode = 'XXX'
    modem = XMODEM(getc=dummy_getc, putc=dummy_putc, mode=mode)
    # exercise
    with pytest.raises(ValueError):
        status = modem.send(BytesIO(b'dummy-stream'))


@pytest.mark.parametrize('mode', ['xmodem', 'xmodem1k'])
def test_xmodem_dummy_fails_send(mode):
    # given,
    modem = XMODEM(getc=dummy_getc, putc=dummy_putc, mode=mode)
    # exercise
    status = modem.send(BytesIO(b'dummy-stream'))
    # verify
    assert not status, ("Expected value of status `False'")


@pytest.mark.parametrize('mode', ['xmodem', 'xmodem1k'])
@pytest.mark.parametrize('stream_data', [BytesIO(b'dummy-stream ' * 17),
                                         BytesIO(b'dummy-stream ' * 1000)])
def test_xmodem_send_exceed_maximum_number_of_resend(mode, stream_data):
    """ Verify send(retry=n) after 'n' transfer failures of single block. """

    # given,
    max_resend = 3

    def getc_generator():
        if mode == 'xmodem':
            yield NAK
        else:
            # xmodem1k
            yield CRC

        if mode == 'xmodem':
            yield ACK

        for i in range(max_resend + 1):
            yield None

        while True:
            yield ACK

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc, mode=mode)

    # exercise
    result = xmodem.send(stream=stream_data, retry=max_resend)

    # verify
    assert not result


@pytest.mark.parametrize('mode', ['xmodem', 'xmodem1k'])
@pytest.mark.parametrize('stream_data', [BytesIO(b'dummy-stream ' * 17),
                                         BytesIO(b'dummy-stream ' * 1000)])
def test_xmodem_send_fails_once_each_packet(mode, stream_data):
    """ Verify send(retry=n) under 'n' transfer failures of single block. """
    # given,
    max_resend = 1

    def getc_generator():
        if mode == 'xmodem':
            yield NAK
        else:
            # xmodem1k
            yield CRC

        while True:
            # fail
            yield None

            # succeed
            yield ACK

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc, mode=mode)

    # exercise
    result = xmodem.send(stream=stream_data, retry=max_resend)

    # verify
    assert result
