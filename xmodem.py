"""
XMODEM file transfer protocol
$Id: $
"""
__author__ = 'Wijnand Modderman <maze@pyth0n.org>'
__copyright__ = ['Copyright (c) 2010 Wijnand Modderman',
                 'Copyright (c) 1981 Chuck Forsberg']
__license__ = 'MIT'
__url__ = 'http://maze.io/'

# Protocol bytes
SOH = chr(0x01)
STX = chr(0x02)
EOT = chr(0x04)
ACK = chr(0x06)
NAK = chr(0x15)
CAN = chr(0x18)
CRC = chr(0x43)

class XMODEM(object):
    '''
    XMODEM Protocol handler, expects an object to read from and an object to 
    write to.

    >>> def getc(size, timeout=1):
    ...     return data or None
    ...
    >>> def putc(data, timeout=1):
    ...     return size or None
    ...
    >>> x = xmodem(getc, putc)

    '''

    crctable = []

    def __init__(self, getc, putc):
        self.getc = getc
        self.putc = putc
        for i in xrange(0, 0xff):
            self.crctable.append(self.generate_crc(i, 0x1021, 0))

    def abort(self, count=3, timeout=60):
        for x in xrange(0, count):
            self.putc(CAN, timeout)

    def send(self, stream, retry=16, timeout=60):
        '''
        Send a stream via the XMODEM protocol.

        >>> stream = file('/etc/issue', 'rb')
        >>> print x.send(stream)
        True
        '''

        # initialize protocol
        error_count = 0
        crc_mode = 0
        while True:
            c = self.getc(1)
            if c:
                if c == NAK:
                    break
                elif c == CRC:
                    crc_mode = 1
                    break
                elif c == CAN:
                    if cancel:
                        return False
                    else:
                        cancel = 1
                else:
                    print 'send ERROR expected NAK, got', ord(c)
            
            error_count += 1
            if error_count >= retry:
                self.abort(timeout=timeout)
                return False

        # send data
        error_count = 0
        packet_size = 128
        sequence = 1
        while True:
            d = stream.read(packet_size)
            if not d:
                print 'send EOS'
                # end of stream
                break 
    
            d = d.ljust(packet_size, '\xff')
            if crc_mode:
                s = self.calc_crc(d)
            else:
                s = self.calc_checksum(d)
            
            # emit packet
            while True:
                self.putc(SOH)
                self.putc(chr(sequence))
                self.putc(chr(0xfe - sequence))
                self.putc(d)
                if crc_mode:
                    self.putc(chr(s >> 8))
                    self.putc(chr(s & 0xff))
                else:
                    self.putc(chr(s))

                c = self.getc(1, timeout)
                if c == ACK: break
                if c == NAK:
                    error_count += 1
                    if error_count >= retry:
                        # excessive amounts of retransmissions requested, 
                        # abort transfer
                        self.abort(timeout=timeout)
                        return False
    
                # protocol error
                self.abort(timeout=timeout)
                return False

            # keep track of sequence
            sequence = (sequence + 1 ) % 0xff

        # end of transmission
        self.putc(EOT)
        return True

    def recv(self, stream, retry=16, timeout=60):
        '''
        Receive a stream via the XMODEM protocol.

        >>> stream = file('/etc/issue', 'wb')
        >>> print x.recv(stream)
        2342
        '''

        # initiate protocol
        error_count = 0
        c = 0
        crc_mode = 1
        cancel = 0
        while True:
            # first try CRC mode, if this fails,
            # fall back to checksum mode
            if error_count < (retry / 2):
                self.putc(CRC)
            else:
                crc_mode = 0
                self.putc(NAK)

            c = self.getc(1, timeout)
            if c in [SOH, STX, CAN]:
                break
            elif c == CAN:
                if cancel:
                    return None
                else:
                    cancel = 1
            else:
                error_count += 1
                if error_count >= retry:
                    # failed to initiate protocol
                    self.abort(timeout=timeout)
                    return None

        # read data
        error_count = 0
        income_size = 0
        packet_size = 128
        sequence = 1
        cancel = 0
        while True:
            while True:
                c = c 
                if c == SOH:
                    packet_size = 128
                    break
                elif c == STX:
                    packet_size = 1024
                    break
                elif c == EOT:
                    return income_size
                elif c == CAN:
                    # cancel at two consecutive cancels
                    if cancel:
                        return None
                    else:
                        cancel = 1
                else:
                    print 'recv ERROR expected SOH/EOT, got', ord(c)
                    error_count += 1
                    if error_count >= retry:
                        self.abort()
                        return None

            # read sequence
            error_count = 0
            cancel = 0
            s1 = ord(self.getc(1))
            s2 = 0xfe - ord(self.getc(1))
            if s1 == sequence and s2 == sequence:
                # sequence is ok, read packet
                data = self.getc(packet_size + 1 + crc_mode) # packet_size + checksum
                if crc_mode:
                    csum = (ord(data[-2]) << 8) + ord(data[-1])
                    data = data[:-2]
                    print 'CRC(%04x <> %04x)' % (csum, self.calc_crc(data)),
                    valid = csum == self.calc_crc(data)
                else:
                    csum = data[-1]
                    data = data[:-1]
                    print 'checksum(%02x <> %02x)' % (ord(csum), self.calc_checksum(data)),
                    valid = ord(csum) == self.calc_checksum(data)

                # valid data, append chunk
                if valid:
                    income_size += len(data)
                    stream.write(data)
                    self.putc(ACK)
                    sequence = (sequence + 1) % 0xff
                    c = self.getc(1, timeout) 
                    continue
            
            # something went wrong, request retransmission
            self.putc(NAK)

    def calc_checksum(self, data):
        return sum(map(ord, data)) % 256

    def calc_crc(self, data, crc=0):
        for char in data:
            crc = (crc >> 8) ^ self.crctable[(crc ^ ord(char)) & 0xff]
        return crc

    def generate_crc(self, data, genpoly, accum):
        if type(data) != int:
            data = chr(data)
        crc = data << 8
        for j in xrange(8):
            crc <<= 1
            if crc & 0x10000:
                crc ^= genpoly
        return crc & 0xffff

