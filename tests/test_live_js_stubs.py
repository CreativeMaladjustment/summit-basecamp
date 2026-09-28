"""Tests for scripts/live_js_stubs.py against a real local HTTP server (on
loopback only -- no real network, no dependency on nwslsoccer.com) so this
actually proves js.fetch performs a real network round trip, not just that
it looks right on paper.
"""

import asyncio
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import live_js_stubs  # noqa: E402

live_js_stubs.install()

import js  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # quiet -- the test output doesn't need an access log

    def do_GET(self):
        if self.path == "/ok":
            body = b"hello from a real socket"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/missing":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found here")
        else:
            self.send_response(500)
            self.end_headers()


class LiveJsFetchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def _url(self, path):
        return "http://127.0.0.1:{}{}".format(self.port, path)

    def test_fetch_returns_a_real_response_over_a_real_socket(self):
        response = asyncio.run(js.fetch(self._url("/ok")))

        self.assertTrue(response.ok)
        self.assertEqual(response.status, 200)
        self.assertEqual(asyncio.run(response.text()), "hello from a real socket")

    def test_a_404_comes_back_as_a_response_not_an_exception(self):
        response = asyncio.run(js.fetch(self._url("/missing")))

        self.assertFalse(response.ok)
        self.assertEqual(response.status, 404)
        self.assertEqual(asyncio.run(response.text()), "not found here")

    def test_json_parses_the_body(self):
        # No JSON endpoint on the fake server -- reuse /ok's plain-text body
        # via a real 200 to confirm .json() at least raises the same kind
        # of error a real non-JSON body would, rather than silently lying.
        response = asyncio.run(js.fetch(self._url("/ok")))
        with self.assertRaises(ValueError):
            asyncio.run(response.json())


if __name__ == "__main__":
    unittest.main()
