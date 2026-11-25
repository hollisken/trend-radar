import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from radar.fetch import get


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ok":
            body = b"x" * 500
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/forbidden":
            self.send_response(403)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


class FetchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_ok_and_truncation(self):
        result = get(self.base + "/ok", max_bytes=100, min_interval=0)
        self.assertTrue(result.ok)
        self.assertEqual(len(result.body), 100)

    def test_http_error_is_recorded_not_raised(self):
        result = get(self.base + "/forbidden", min_interval=0)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "http_403")

    def test_missing_path_is_404(self):
        result = get(self.base + "/nope", min_interval=0)
        self.assertEqual(result.error, "http_404")

    def test_bad_scheme(self):
        result = get("ftp://example.com/file")
        self.assertEqual(result.error, "bad_scheme")

    def test_unreachable_port(self):
        result = get("http://127.0.0.1:9/", timeout=1, min_interval=0)
        self.assertFalse(result.ok)
        self.assertTrue(result.error.startswith("transport_"))


if __name__ == "__main__":
    unittest.main()
