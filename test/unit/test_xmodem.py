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
                               if rec.message in (
                                   "send error: expected NAK, CRC, EOT or CAN; got b'\\xde'",  # py3
                                   "send error: expected NAK, CRC, EOT or CAN; got '\\xde'")   # py2
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


def _make_block(sequence, packet_size, data=None, crc_mode=1, corrupt_crc=False):
    """
    Build a complete XMODEM data block (sequence + payload + checksum).

    Returns bytes suitable for yielding from a mock getc generator when
    the recv() method performs its batched read of
    ``2 + packet_size + 1 + crc_mode`` bytes.
    """
    modem = XMODEM(getc=dummy_getc, putc=dummy_putc)
    seq1 = sequence & 0xff
    seq2 = 0xff - seq1
    if data is None:
        data = b'\x00' * packet_size
    else:
        data = data.ljust(packet_size, b'\x1a')
    if crc_mode:
        crc = modem.calc_crc(data)
        if corrupt_crc:
            crc ^= 0xffff
        checksum = bytes([crc >> 8, crc & 0xff])
    else:
        csum = modem.calc_checksum(data)
        if corrupt_crc:
            csum ^= 0xff
        checksum = bytes([csum])
    return bytes([seq1, seq2]) + data + checksum


def test_xmodem1k_receive_successful_when_timeout_after_first_packet(monkeypatch):
    """Verify recv recovery from timeout directly after first packet.

    With the batched-read optimization, after getting a bad header char
    (None/timeout), recv breaks out of the header loop and performs a
    batched read which also times out, then purges and NAKs.
    """
    # given,
    max_resend = 3
    mode = 'xmodem1k'
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    progress_records = []
    def callback(total_packets, success_count, error_count, packet_size):
        record = {'total_packets': total_packets, 'success_count': success_count,
                  'error_count': error_count, 'packet_size': packet_size}
        logging.debug('callback: %r', record)
        progress_records.append(record)

    def getc_generator():
        # start sequence: getc(1)
        yield STX

        # first block batched read: getc(2 + 1024 + 1 + 1)
        yield _make_block(1, 1024, crc_mode=1)

        # next header: getc(1) -> timeout
        yield None

        # batched read after bad header: getc(1028) -> timeout
        yield None

        # purge: getc(1) -> timeout (purge ends)
        yield None

        # next header after NAK: getc(1)
        yield STX

        # second block batched read: getc(1028)
        yield _make_block(2, 1024, crc_mode=1)

        # end of transmission: getc(1)
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc, mode=mode)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=max_resend, callback=callback)

    # verify
    assert result == 2048  # 2 x 1024 bytes


def test_xmodem_recv_successful_single_block(monkeypatch):
    """Verify recv() succeeds for a single-block transfer with CRC mode."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    payload = b'Hello XMODEM!' + b'\x00' * (128 - 13)

    def getc_generator():
        # start sequence: getc(1)
        yield SOH

        # batched read: getc(2 + 128 + 1 + 1)
        yield _make_block(1, 128, data=b'Hello XMODEM!', crc_mode=1)

        # next header: getc(1) -> EOT
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=16)

    # verify
    assert result == 128
    destination.seek(0)
    received = destination.read()
    assert received[:13] == b'Hello XMODEM!'


def test_xmodem_recv_successful_multi_block(monkeypatch):
    """Verify recv() succeeds for a multi-block transfer."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    def getc_generator():
        # start sequence
        yield SOH

        # block 1
        yield _make_block(1, 128, data=b'\xaa' * 128, crc_mode=1)

        # block 2 header
        yield SOH

        # block 2
        yield _make_block(2, 128, data=b'\xbb' * 128, crc_mode=1)

        # block 3 header
        yield SOH

        # block 3
        yield _make_block(3, 128, data=b'\xcc' * 128, crc_mode=1)

        # end of transmission
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=16)

    # verify
    assert result == 384  # 3 x 128 bytes
    destination.seek(0)
    assert destination.read(128) == b'\xaa' * 128
    assert destination.read(128) == b'\xbb' * 128
    assert destination.read(128) == b'\xcc' * 128


def test_xmodem_recv_bad_sequence_number(monkeypatch):
    """Verify recv() handles bad sequence numbers by NAKing and retrying."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    def getc_generator():
        # start sequence
        yield SOH

        # block with WRONG sequence (5 instead of 1)
        yield _make_block(5, 128, crc_mode=1)

        # purge: getc(1) -> timeout
        yield None

        # retransmission after NAK: header
        yield SOH

        # block with CORRECT sequence
        yield _make_block(1, 128, crc_mode=1)

        # end of transmission
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=16)

    # verify: transfer should succeed after retry
    assert result == 128


def test_xmodem_recv_bad_sequence_complement(monkeypatch):
    """Verify recv() rejects blocks where seq2 != 0xff - seq1."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    modem = XMODEM(getc=dummy_getc, putc=dummy_putc)
    # Build a block with mismatched complement: seq1=1, seq2=0x00 (should be 0xFE)
    data = b'\x00' * 128
    crc = modem.calc_crc(data)
    bad_block = bytes([0x01, 0x00]) + data + bytes([crc >> 8, crc & 0xff])

    def getc_generator():
        # start sequence
        yield SOH

        # block with bad complement
        yield bad_block

        # purge -> timeout
        yield None

        # retransmission: correct block
        yield SOH
        yield _make_block(1, 128, crc_mode=1)

        # end
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=16)

    # verify: should succeed after retry with correct block
    assert result == 128


def test_xmodem_recv_bad_crc(monkeypatch):
    """Verify recv() handles corrupted CRC by requesting retransmission."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    def getc_generator():
        # start sequence
        yield SOH

        # block with corrupted CRC
        yield _make_block(1, 128, crc_mode=1, corrupt_crc=True)

        # purge -> timeout
        yield None

        # retransmission after NAK: correct block
        yield SOH
        yield _make_block(1, 128, crc_mode=1)

        # end
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=16)

    # verify: should succeed after retry
    assert result == 128


def test_xmodem_recv_short_block(monkeypatch):
    """Verify recv() handles short (badly sized) blocks gracefully."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    # A short block: only 10 bytes instead of 2 + 128 + 1 + 1 = 132
    # Use non-zero data to ensure CRC mismatch (CRC of zeros is zero)
    short_data = b'\x01\xfe' + b'\xaa' * 8

    def getc_generator():
        # start sequence
        yield SOH

        # short block (badly sized)
        yield short_data

        # purge -> timeout
        yield None

        # retransmission: correct block
        yield SOH
        yield _make_block(1, 128, crc_mode=1)

        # end
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=16)

    # verify: should succeed after retry with correct block
    assert result == 128


def test_xmodem_recv_very_short_block_does_not_crash(monkeypatch):
    """Verify recv() NAKs instead of crashing on a 3-byte block."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    # 3 bytes total: correct sequence (0x01, 0xfe) + 1 data byte.
    # After stripping the 2 sequence bytes, only 1 byte remains —
    # far too short for _verify_recv_checksum to extract CRC bytes.
    very_short = bytes([0x01, 0xfe, 0xaa])

    def getc_generator():
        yield SOH

        # very short block — should NAK, not IndexError
        yield very_short

        # purge -> timeout
        yield None

        # retransmission: correct block
        yield SOH
        yield _make_block(1, 128, crc_mode=1)

        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=16)

    assert result == 128


def test_xmodem_recv_timeout_on_block_read(monkeypatch):
    """Verify recv() handles timeout during block data read."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    def getc_generator():
        # start sequence
        yield SOH

        # timeout on block data read (None = timeout)
        yield None

        # purge -> timeout
        yield None

        # retransmission: header
        yield SOH

        # correct block
        yield _make_block(1, 128, crc_mode=1)

        # end
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=16)

    # verify: should succeed after retry
    assert result == 128


def test_xmodem_recv_checksum_mode(monkeypatch):
    """Verify recv() works in checksum mode (crc_mode=0)."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    def getc_generator():
        # start sequence
        yield SOH

        # block with checksum (not CRC)
        yield _make_block(1, 128, crc_mode=0)

        # end
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, crc_mode=0, retry=16)

    # verify
    assert result == 128


def test_xmodem_recv_cancel_by_can_can(monkeypatch):
    """Verify recv() is cancelled when 2xCAN is received during data phase."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    def getc_generator():
        # start sequence
        yield SOH

        # first block - success
        yield _make_block(1, 128, crc_mode=1)

        # instead of next block, receive CAN CAN
        yield CAN
        yield CAN

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=16)

    # verify: cancelled, returns None
    assert result is None


def test_xmodem_recv_single_can_does_not_abort(monkeypatch):
    """Verify recv() does not abort on a single CAN byte in the header."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    def getc_generator():
        # start sequence
        yield SOH

        # first block - success
        yield _make_block(1, 128, crc_mode=1)

        # single CAN (could be line noise)
        yield CAN

        # followed by valid header, NOT a second CAN
        yield SOH

        # second block
        yield _make_block(2, 128, crc_mode=1)

        # end of transmission
        yield EOT

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        return next(mock)

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=16)

    assert result == 256


def test_xmodem_recv_exceeds_retry_limit(monkeypatch):
    """Verify recv() aborts after exceeding retry limit on repeated errors."""
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    retry = 3

    def getc_generator():
        # start sequence
        yield SOH

        # keep sending bad blocks until retry limit exceeded
        for _ in range(retry + 2):
            yield _make_block(1, 128, crc_mode=1, corrupt_crc=True)
            # purge
            yield None
            # next header
            yield SOH

    mock = getc_generator()

    def mock_getc(size, timeout=1):
        try:
            return next(mock)
        except StopIteration:
            return None

    xmodem = XMODEM(getc=mock_getc, putc=dummy_putc)

    # exercise
    destination = BytesIO()
    result = xmodem.recv(stream=destination, retry=retry)

    # verify: should abort (return None)
    assert result is None
