"""Tests for the uptime monitor, run against a local HTTP server."""

from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import monitor  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/ok":
            body = b"hello"
            self.send_response(200)
        elif self.path == "/teapot":
            body = b"nope"
            self.send_response(418)
        else:
            body = b"missing"
            self.send_response(404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_ok_endpoint(self):
        r = monitor.check("ok", self.base + "/ok")
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], 200)
        self.assertIsNotNone(r["latency_ms"])
        self.assertIn("HTTP 200", r["detail"])

    def test_wrong_expectation_is_a_failure(self):
        r = monitor.check("ok", self.base + "/ok", expect=201)
        self.assertFalse(r["ok"])
        self.assertIn("expected 201", r["detail"])

    def test_4xx_is_reported_not_raised(self):
        r = monitor.check("teapot", self.base + "/teapot")
        self.assertFalse(r["ok"])
        self.assertEqual(r["status"], 418)

    def test_unreachable_is_a_result(self):
        r = monitor.check("dead", "http://127.0.0.1:1/nothing", timeout=2)
        self.assertFalse(r["ok"])
        self.assertIsNone(r["status"])
        self.assertTrue("unreachable" in r["detail"] or "socket" in r["detail"])

    def test_uptime_percentage(self):
        history = [
            {"results": [{"name": "a", "ok": True}, {"name": "b", "ok": False}]},
            {"results": [{"name": "a", "ok": True}, {"name": "b", "ok": True}]},
        ]
        self.assertEqual(monitor.uptime_pct(history, "a"), 100.0)
        self.assertEqual(monitor.uptime_pct(history, "b"), 50.0)
        self.assertIsNone(monitor.uptime_pct(history, "zzz"))

    def test_status_md_renders_a_table(self):
        run = {"checked_at": "2026-01-01T00:00:00+00:00", "results": [
            {"name": "a", "url": "http://x", "ok": True, "status": 200,
             "latency_ms": 12, "detail": "HTTP 200", "checked_at": ""},
        ]}
        original = monitor.ROOT
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            monitor.ROOT = Path(tmp)
            try:
                monitor.write_status_md(run, [])
                text = (Path(tmp) / "STATUS.md").read_text()
            finally:
                monitor.ROOT = original
        self.assertIn("| endpoint | now |", text)
        self.assertIn("| a | up |", text)

    def test_targets_file_is_valid(self):
        targets = monitor.load_targets()
        self.assertTrue(targets)
        for t in targets:
            self.assertIn("name", t)
            self.assertTrue(t["url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
