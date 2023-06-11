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
import time
import logging

# local
from xmodem import NAK, CRC, ACK, XMODEM, STX, SOH, EOT, CAN

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
def test_xmodem_fails_when_send_exceed_maximum_number_of_resend(mode):
    """ Verify send(retry=n) fails after 'n' transfer failures of single block. """

    # given,
    max_resend = 3
    stream_data = BytesIO(b'dummy-stream')

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

    progress_records = []
    def callback(total_packets, success_count, error_count):
        record = {'total_packets': total_packets, 'success_count': success_count,
                  'error_count': error_count}
        logging.debug('callback: %r', record)
        progress_records.append(record)
    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc, mode=mode)

    # exercise
    result = xmodem.send(stream=stream_data, retry=max_resend, callback=callback)

    # verify
    assert not result
    if mode == 'xmodem':
        assert progress_records == [
            {'error_count': 0, 'success_count': 1, 'total_packets': 1},
            {'error_count': 1, 'success_count': 1, 'total_packets': 1},
            {'error_count': 2, 'success_count': 1, 'total_packets': 1},
            {'error_count': 3, 'success_count': 1, 'total_packets': 1},
            {'error_count': 4, 'success_count': 1, 'total_packets': 1}]

    elif mode == 'xmodem1k':
        assert progress_records == [
            {'total_packets': 1, 'success_count': 0, 'error_count': 1},
            {'total_packets': 1, 'success_count': 0, 'error_count': 2},
            {'total_packets': 1, 'success_count': 0, 'error_count': 3},
            {'total_packets': 1, 'success_count': 0, 'error_count': 4}
        ]

@pytest.mark.parametrize('mode', ['xmodem', 'xmodem1k'])
def test_xmodem_send_cancelled_by_can_can(mode):
    """ Verify send() is cancelled when CAN CAN is received at start-sequence. """

    # given,
    def getc_generator():
        yield CAN
        yield CAN

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc, mode=mode)

    # exercise
    result = xmodem.send(stream=BytesIO())

    # verify failure to send
    assert not result

@pytest.mark.parametrize('mode', ['xmodem', 'xmodem1k'])
def test_xmodem_send_cancelled_by_eot(mode):
    """ Verify send() is cancelled when EOT is received at start-sequence. """

    # given,
    def getc_generator():
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc, mode=mode)

    # exercise
    result = xmodem.send(stream=BytesIO())

    # verify failure to send
    assert not result

@pytest.mark.parametrize('mode', ['xmodem', 'xmodem1k'])
def test_xmodem_send_fails_by_garbage_start_sequence(mode, monkeypatch, caplog):
    """ Verify send() fails when garbage bytes are received and number of retries are exceeded. """

    monkeypatch.setattr(time, 'sleep', lambda t: None)

    # given the same number of 'garbage' bytes as retry,
    retry = 4
    num_garbage_bytes = retry + 1
    def getc_generator():
        for n in range(num_garbage_bytes):
            yield b'\xde'

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc, mode=mode)

    # exercise
    result_stream = BytesIO(b'123')
    result = xmodem.send(stream=result_stream, retry=retry)

    # verify failure to send
    assert not result
    error_logged_send_error = [rec for rec in caplog.records
                               if rec.message == "send error: expected NAK, CRC, EOT or CAN; got b'\\xde'"
                               and rec.levelno == logging.ERROR]
    assert len(error_logged_send_error) == retry + 1

    error_logged_aborts = [rec for rec in caplog.records
                           if rec.message == "send error: error_count reached {}, aborting.".format(retry)
                           and rec.levelno == logging.ERROR]
    assert len(error_logged_aborts) == 1
    # verify no data is sent, sending stream is never read, position in file does not advance
    assert result_stream.tell() == 0


@pytest.mark.parametrize('mode', ['xmodem', 'xmodem1k'])
@pytest.mark.parametrize('stream_data', [BytesIO(b'dummy-stream ' * 17),
                                         BytesIO(b'dummy-stream ' * 1000)])
def test_xmodem_send_succeeds_when_timeout_every_other_packet(mode, stream_data):
    """ Verify send(retry=n) succeeds when every other ACK times out."""
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


def test_xmodem1k_receive_successful_when_timeout_after_first_packet(monkeypatch):
    """ Verify recv reaction to timeout directly after first packet """
    # given,
    max_resend = 1
    mode = 'xmodem1k'
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    progress_records = []
    def callback(total_packets, success_count, error_count, packet_size):
        record = {'total_packets': total_packets, 'success_count': success_count,
                  'error_count': error_count, 'packet_size': packet_size}
        logging.debug('callback: %r', record)
        progress_records.append(record)

    def getc_generator():
        yield STX

        # first packet sequence
        yield b'\x01'
        yield b'\xfe'

        yield bytes(1024+1+1)

        # timeout
        yield None

        # second packet
        yield STX
        yield b'\x02'
        yield b'\xfd'

        yield bytes(1024+1+1)

        # end of transmission
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc, mode=mode)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=max_resend, callback=callback)

    # verify
    assert result

    assert len(progress_records) == 4
    assert progress_records == [
        {'total_packets': 1, 'success_count': 1, 'error_count': 0, 'packet_size': 1024},
        {'total_packets': 1, 'success_count': 1, 'error_count': 1, 'packet_size': 1024},
        {'total_packets': 2, 'success_count': 2, 'error_count': 0, 'packet_size': 1024},
        {'total_packets': 2, 'success_count': 2, 'error_count': 0, 'packet_size': 1024},
    ]
