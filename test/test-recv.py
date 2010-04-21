import select
import subprocess
import sys
import StringIO
from xmodem import XMODEM

if __name__ == '__main__':
    pipe   = subprocess.Popen(['sx', '--xmodem', __file__], 
                 stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    si, so = (pipe.stdin, pipe.stdout)

    def getc(size, timeout=3):
        w,t,f = select.select([so], [], [], timeout)
        if w:
            data = so.read(size)
        else:
            data = None

        print 'getc(', repr(data), ')'
        return data

    def putc(data, timeout=3):
        w,t,f = select.select([], [si], [], timeout)
        if t:
            si.write(data)
            si.flush()
            size = len(data)
        else:
            size = None

        print 'putc(', repr(data), repr(size), ')'
        return size

    stream = StringIO.StringIO()
    xmodem = XMODEM(getc, putc)
    nbytes = xmodem.recv(stream, retry=8)

    print >> sys.stderr, 'received', nbytes, 'bytes'
    print >> sys.stderr, stream.getvalue()

    sys.exit(int(nbytes == 0))

