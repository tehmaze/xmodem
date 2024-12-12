from xmodem import XMODEM
from xmodem import XMODEM1k
from xmodem import _send as send
import serial
import sys
import time

def send_file():
    ser = serial.Serial('COM1', timeout=0, baudrate=115200) # or whatever port you need

    def getc(size, timeout=1):
        ser.timeout = timeout
        retData = ser.read(size)
        print(retData)
        return retData

    def putc(data, timeout=1):
        ser.timeout = timeout
        return ser.write(data)  # note that this ignores the timeout   testing: rate: 12.264k

    def callback(total_packets, success_count, error_count):
        print("total packets are:{}, success packets are:{}, error packets are:{}".format(total_packets, success_count, error_count))
        


    modem = XMODEM1k(getc, putc)

    print('Start to send file ...\n')


    if False:
        with open('./data.bin', 'wb') as stream:
            #modem.send(stream=stream)
            for _ in range(1024*10):
                stream.write('0123456789'.encode())
    else:
        with open('./data.bin', 'rb') as stream:
            start = time.time_ns()//1000000
            modem.send(stream=stream, timeout=1, callback=callback)
            print(time.time_ns()//1000000 - start)

def send_from_buffer():
    ser = serial.Serial('COM1', timeout=0, baudrate=115200) # or whatever port you need

    def getc(size, timeout=1):
        ser.timeout = timeout
        retData = ser.read(size)
        print(retData)
        return retData

    def putc(data, timeout=1):
        ser.timeout = timeout
        return ser.write(data)  # note that this ignores the timeout   testing: rate: 12.264k

    def callback(total_packets, success_count, error_count):
        print("total packets are:{}, success packets are:{}, error packets are:{}".format(total_packets, success_count, error_count))
        


    modem = XMODEM1k(getc, putc)

    print('Start to send file ...\n')
    data_to_send = bytearray(range(255))
    for _ in range(4):
        data_to_send.extend(data_to_send)

    start = time.time_ns()//1000000
    modem.send_bytes(data_src=data_to_send, timeout=1, callback=callback)
    print(time.time_ns()//1000000 - start)

if __name__ == "__main__":
    # send_from_buffer()
    send_file()




