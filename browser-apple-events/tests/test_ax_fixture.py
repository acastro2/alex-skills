"""Real loopback HTTP/SQLite fixture checks. These do not exercise a browser."""

import json
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from urllib.error import HTTPError
from urllib.request import build_opener, ProxyHandler, Request

from ax_fixture import Fixture


class FixtureTests(unittest.TestCase):
    def test_two_origins_save_and_read_independent_revision_and_rejection(self):
        http = build_opener(ProxyHandler({}))
        with Fixture() as fixture:
            self.assertNotEqual(fixture.top_origin, fixture.frame_origin)
            with http.open(fixture.url, timeout=3) as response:
                self.assertEqual(response.status, 200)
            with http.open(fixture.frame_origin + "/approval", timeout=3) as response:
                self.assertEqual(response.status, 200)
            request = Request(fixture.frame_origin + "/event", data=b'{"action":"submit"}', headers={"Content-Type": "application/json"})
            with http.open(request, timeout=3) as response:
                self.assertEqual(json.load(response)["revision"], 2)
            self.assertEqual(fixture.readback()["state"], "Pending")
            request = Request(fixture.frame_origin + "/event", data=b'{"action":"reject","reason":""}', headers={"Content-Type": "application/json"})
            with self.assertRaises(HTTPError):
                http.open(request, timeout=3)
            self.assertEqual(fixture.readback()["revision"], 2)
            request = Request(fixture.frame_origin + "/event", data=b'{"action":"reject","reason":"validation only"}', headers={"Content-Type": "application/json"})
            with http.open(request, timeout=3) as response:
                self.assertEqual(json.load(response)["revision"], 3)
            self.assertEqual(fixture.readback(), {"record": "FIXTURE-1", "state": "New", "revision": 3, "reason": "validation only", "pci": 0})

    def test_failure_cleanup_stops_both_listeners_and_threads(self):
        with self.assertRaisesRegex(RuntimeError, "fixture failure"):
            with Fixture() as fixture:
                addresses = [server.server_address for server in fixture.servers]
                raise RuntimeError("fixture failure")
        self.assertTrue(all(not thread.is_alive() for thread in fixture.threads))
        for address in addresses:
            with self.subTest(address=address), self.assertRaises(OSError):
                socket.create_connection(address, timeout=0.2)
        self.assertFalse(fixture.database.exists())

    def test_retired_live_runner_refuses_even_with_both_approvals(self):
        script = Path(__file__).with_name("live_ax_check.py")
        result = subprocess.run([sys.executable, str(script), "--app", "/does/not/exist",
            "--allow-test-windows", "--browser-owner-coordinated"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["error"]["code"], "AX_WRITES_DISABLED")
        self.assertEqual(json.loads(result.stdout)["error"]["outcome"], "not_started")

    def test_live_runner_requires_both_approvals_before_any_browser_access(self):
        script = Path(__file__).with_name("live_ax_check.py")
        for flags in ([], ["--allow-test-windows"], ["--browser-owner-coordinated"]):
            result = subprocess.run([sys.executable, str(script), "--app", "/does/not/exist", *flags], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Need disposable-window approval", result.stderr)


if __name__ == "__main__":
    unittest.main()
