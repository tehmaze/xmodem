import os
import select
import subprocess
import sys
import StringIO
import tempfile
from xmodem import XMODEM

if __name__ == '__main__':
    fd, fn = tempfile.mkstemp()
    pipe   = subprocess.Popen(['rx', '--xmodem', fn], 
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

    stream = open(__file__, 'rb')
    xmodem = XMODEM(getc, putc)
    status = xmodem.send(stream, retry=8)
    stream.close()

    print >> sys.stderr, 'sent', status
    print >> sys.stderr, file(fn).read()

    os.unlink(fn)

    sys.exit(int(not status))

