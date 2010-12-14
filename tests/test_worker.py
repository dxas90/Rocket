# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

# Import System Modules
import sys
import errno
import socket
import unittest
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

try:
    from io import StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

# Import Custom Modules
from rocket import worker

# Constants
SAMPLE_HEADERS = '''\
GET /dumprequest HTTP/1.1
Host: djce.org.uk
User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.12) Gecko/20101027 Ubuntu/10.04 (lucid) Firefox/3.6.12
Accept: text/html,application/xhtml+xml
 application/xml;q=0.9,*/*;q=0.8
Accept-Language: en-us,en;q=0.5
Accept-Encoding: gzip,deflate
Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7
Keep-Alive: 115
Connection: keep-alive
Referer: http://www.google.com/custom?hl=en&client=pub-9300639326172081&cof=FORID%3A13%3BAH%3Aleft%3BCX%3AUbuntu%252010%252E04%3BL%3Ahttp%3A%2F%2Fwww.google.com%2Fintl%2Fen%2Fimages%2Flogos%2Fcustom_search_logo_sm.gif%3BLH%3A30%3BLP%3A1%3BLC%3A%230000ff%3BVLC%3A%23663399%3BDIV%3A%23336699%3B&adkw=AELymgUf3P4j5tGCivvOIh-_XVcEYuoUTM3M5ETKipHcRApl8ocXgO_F5W_FOWHqlk4s4luYT_xQ10u8aDk2dEwgEYDYgHezJRTj7dx64CHnuTwPVLVChMA&channel=6911402799&q=http+request+header+sample&btnG=Search&cx=partner-pub-9300639326172081%3Ad9bbzbtli15'''
HEADER_DICT = {
    'host': 'djce.org.uk',
    'user_agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.12) Gecko/20101027 Ubuntu/10.04 (lucid) Firefox/3.6.12',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'accept_language': 'en-us,en;q=0.5',
    'accept_encoding': 'gzip,deflate',
    'accept_charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'keep_alive': '115',
    'connection': 'keep-alive',
    'referer': 'http://www.google.com/custom?hl=en&client=pub-9300639326172081&cof=FORID%3A13%3BAH%3Aleft%3BCX%3AUbuntu%252010%252E04%3BL%3Ahttp%3A%2F%2Fwww.google.com%2Fintl%2Fen%2Fimages%2Flogos%2Fcustom_search_logo_sm.gif%3BLH%3A30%3BLP%3A1%3BLC%3A%230000ff%3BVLC%3A%23663399%3BDIV%3A%23336699%3B&adkw=AELymgUf3P4j5tGCivvOIh-_XVcEYuoUTM3M5ETKipHcRApl8ocXgO_F5W_FOWHqlk4s4luYT_xQ10u8aDk2dEwgEYDYgHezJRTj7dx64CHnuTwPVLVChMA&channel=6911402799&q=http+request+header+sample&btnG=Search&cx=partner-pub-9300639326172081%3Ad9bbzbtli15'}
SENDALL_VALUES = [
    '''HTTP/1.1 200 OK\nContent-Length: 2\nContent-Type: text/plain\n\nOK\n''',
    '''HTTP/1.1 400 Bad Request\nContent-Length: 11\nContent-Type: text/plain\n\nBad Request\n''',
]
REQUEST_DICT = {
    'GET /dir1/dir2/file1.html?a=1&b=2 HTTP/1.1': \
        dict(path='/dir1/dir2/file1.html',
            query_string='a=1&b=2',
            scheme='',
            host='',
            method='GET',
            protocol='HTTP/1.1'
        ),
    'POST https://example.com/file1.html HTTP/1.0': \
        dict(path='/file1.html',
            query_string='',
            scheme='https',
            host='example.com',
            method='POST',
            protocol='HTTP/1.0'
        ),
    'OPTIONS * HTTP/1.0': \
        dict(path='*',
            query_string='',
            scheme='',
            host='',
            method='OPTIONS',
            protocol='HTTP/1.0'
        ),
}
BAD_REQUESTS = [
    'GET /dir1/dir2/file1.html?a=1&b=2 SPDY/1.1',
    'GET /dir1/dir2/file1.html?a=1&b=2HTTP/1.1',
    'GET/dir1/dir2/file1.html?a=1&b=2 HTTP/1.1',
]

class FakeConn:
    def __init__(self):
        self.closeConnection = True
        self.sentData = None
        self.closed = False
        self.ssl = False
        self.secure = False

    def sendall(self, data):
        self.sendData = data
        if data.lower().strip().endswith("error"):
            raise socket.error
        else:
            assert data in SENDALL_VALUES

    def close(self):
        self.closed = True
    
class FakeVars:
    def __init__(self):
        self.args = list()

# Define Tests
class WorkerTest(unittest.TestCase):
    def setUp(self):
        self.active_queue = Queue()
        self.monitor_queue = Queue()
        self.worker = worker.Worker(dict(), self.active_queue, self.monitor_queue)
        self.starttuple = (socket.socket(), ('127.0.0.1', 90453))
        self.serverport = 81

    def testRunApp(self):
        self.assert_(self.worker.closeConnection,
                     msg="Worker not starting with a fresh connection")

        self.worker.closeConnection = False

        self.worker.conn = FakeConn()

        self.assertRaises(NotImplementedError, self.worker.run_app, self.worker.conn)

        self.assert_(self.worker.closeConnection,
                     msg="Worker.run_app() did not set closeConnection")

    def testSendReponse(self):
        self.worker.conn = FakeConn()

        self.assert_(self.worker.closeConnection,
                     msg="Worker not starting with a fresh connection")

        self.worker.closeConnection = False

        self.worker.send_response("200 OK")

        self.assert_(not self.worker.closeConnection,
                     msg="Worker.send_response() set closeConnection when it shouldn't have")

        self.worker.closeConnection = False

        self.worker.send_response("500 Server Error")

        self.assert_(self.worker.closeConnection,
                     msg="Worker.send_response() did not set closeConnection when it shouldn't have")

    def testReadHeaders(self):
        headersBuf = StringIO('\r\n'.join(SAMPLE_HEADERS.splitlines()[1:]) + '\r\n\r\n')
        headers = self.worker.read_headers(headersBuf)

        for header_name in HEADER_DICT.keys():
            self.assertEqual(headers[header_name], HEADER_DICT[header_name])

    def testReadRequestLine(self):
        for reqline, resdict in REQUEST_DICT.items():
            result = self.worker.read_request_line(StringIO(reqline + '\r\n'))
            for key in result:
                self.assertEqual(result[key], resdict[key])

    def testReadRequestLineErrors(self):
        self.worker.conn = FakeConn()
        for reqline in BAD_REQUESTS:
            self.assertRaises(worker.BadRequest,
                              self.worker.read_request_line,
                              StringIO(reqline + '\r\n'))

    def testHandleError_SSLTimeout(self):
        m = self.worker._handleError

        self.worker.conn = FakeConn()
        self.worker.closeConnection = False

        # Test SSL Socket Timeout
        vars = FakeVars()
        vars.args.append("timed out")
        self.assert_(m(worker.SSLError, vars, None))
        self.assertEqual(self.worker.closeConnection, False)

        conn = self.monitor_queue.get()
        self.assert_(conn is self.worker.conn)

    def testHandleError_SocketTimeout(self):
        m = self.worker._handleError

        self.worker.conn = FakeConn()
        self.worker.closeConnection = False

        # Test Socket Timeout
        self.assert_(m(worker.SocketTimeout, None, None))
        self.assertEqual(self.worker.closeConnection, False)

        conn = self.monitor_queue.get()
        self.assert_(conn is self.worker.conn)

    def testHandleError_BadRequest(self):
        m = self.worker._handleError

        self.worker.conn = FakeConn()
        self.worker.closeConnection = False

        # Test Bad Request
        self.assert_(m(worker.BadRequest, None, None))
        self.assertEqual(self.worker.closeConnection, True)

    def testHandleError_SocketClosed(self):
        m = self.worker._handleError

        self.worker.conn = FakeConn()
        self.worker.closeConnection = False

        # Test Socket Closed
        self.assert_(not m(worker.SocketClosed, None, None))
        self.assertEqual(self.worker.closeConnection, True)

    def testHandleError_SocketError(self):
        m = self.worker._handleError

        vars = FakeVars()
        vars.args.append(errno.ECONNABORTED)

        self.worker.conn = FakeConn()
        self.worker.closeConnection = False

        # Test SocketError
        self.assert_(not m(socket.error, vars, None))
        self.assertEqual(self.worker.closeConnection, True)
        self.assertEqual(self.worker.status, "200 OK")

    def testHandleError_SocketUnknownError(self):
        m = self.worker._handleError

        vars = FakeVars()
        vars.args.append("a")

        self.worker.conn = FakeConn()
        self.worker.closeConnection = False

        # Test Socket Unknown Error
        self.assertRaises(AttributeError, m, socket.error, vars, "traceback")
        self.assertEqual(self.worker.closeConnection, True)
        self.assertEqual(self.worker.status, "999 Utter Server Failure")

    def testHandleError_UnknownError(self):
        m = self.worker._handleError

        vars = FakeVars()
        vars.args.append("a")

        self.worker.conn = FakeConn()
        self.worker.closeConnection = False

        # Test Unknown Error
        self.assert_(not m(RuntimeError, vars, None))
        self.assertEqual(self.worker.closeConnection, True)

    def testRunStopSentryValue(self):
        self.active_queue.put(None)
        
        # NOTE: This test may infinite loop instead of fail.
        self.assertEqual(None, self.worker.run())
    
    def testRun_HTTPConnectionOnHTTPSSocket(self):
        conn = FakeConn()
        conn.ssl = True
        conn.secure = False

        self.active_queue.put(conn)
        self.active_queue.put(None)

        self.worker.closeConnection = False
        
        # NOTE: This test may infinite loop instead of fail.
        self.assertEqual(None, self.worker.run())
        
        # Test that it closed the connection
        self.assert_(self.worker.closeConnection)
        
        # Test that it sent 400 bad request
        self.assertEqual(conn.sendData, 'HTTP/1.1 400 Bad Request\nContent-Length: 11\nContent-Type: text/plain\n\nBad Request\n')
    
    def testRun_HTTPConnection(self):
        conn = FakeConn()

        self.active_queue.put(conn)
        self.active_queue.put(None)

        self.worker.closeConnection = False
        self.worker.request_line = ''
        
        # NOTE: This test may infinite loop instead of fail.
        self.assertEqual(None, self.worker.run())
        
        # Test that it closed the connection
        self.assert_(self.worker.closeConnection)
        
        self.assertEqual(conn.sendData, 'HTTP/1.1 500 Server Error\nContent-Length: 12\nContent-Type: text/plain\n\nServer Error\n')
    

    def tearDown(self):
        del self.worker

if __name__ == '__main__':
    unittest.main()
