from xmodem import XMODEM
from xmodem import XMODEM1k
from xmodem import _send as send
import sys
import serial
import time


def rcv2file():
    ser = serial.Serial('COM2', timeout=0, baudrate=115200) # or whatever port you need

    def getc(size, timeout=1):
        ser.timeout = timeout
        return ser.read(size)

    def putc(data, timeout=1):
        ser.timeout = timeout
        return ser.write(data)  # note that this ignores the timeout

    modem = XMODEM1k(getc, putc)

    print('Wait to receive data ...\n')
    with open('./rcv.bin', 'wb') as stream:
        modem.recv(stream, crc_mode=1, timeout=1)

def rcv2memory():
    ser = serial.Serial('COM2', timeout=0, baudrate=115200) # or whatever port you need

    def getc(size, timeout=1):
        ser.timeout = timeout
        return ser.read(size)

    def putc(data, timeout=1):
        ser.timeout = timeout
        return ser.write(data)  # note that this ignores the timeout

    modem = XMODEM1k(getc, putc)

    print('Wait to receive data ...\n')
    rcvRslt = None
    bufferBytes = bytearray()
    rcvRslt = modem.recv_bytes(bufferBytes, crc_mode=1, timeout=1)
    print(len(bufferBytes), rcvRslt)
    print(bufferBytes[0:])

if __name__ == "__main__":
    rcv2memory()





