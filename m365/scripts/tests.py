#!/usr/bin/env python3
"""Tests for m365.py at its two boundaries: the network and the token cache.

The live behaviour of every command is already proven end to end (see the m365 SKILL.md
for the verified call list). These tests lock down the seams so a refactor cannot change
the error shape, the request shape, or the file permissions without failing.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import m365  # noqa: E402


class FakeCache:
    def __init__(self, data):
        self.data = data
        self.written = None

    def read(self):
        return self.data

    def write(self, tokens):
        self.written = tokens


class TestTokenSeam(unittest.TestCase):
    def test_valid_token_is_returned_without_any_network_call(self):
        def explode(*a, **k):
            raise AssertionError("must not call the token endpoint when the cache is valid")

        cache = FakeCache({"access_token": "cached", "expires_at": 10_000})
        self.assertEqual(m365.access_token(cache, now=lambda: 1_000, post=explode), "cached")

    def test_expired_token_refreshes_and_persists(self):
        calls = []

        def post(url, form):
            calls.append(form)
            return {"access_token": "fresh", "refresh_token": "r2", "expires_in": 3600}

        cache = FakeCache({"access_token": "stale", "refresh_token": "r1", "expires_at": 500})
        self.assertEqual(m365.access_token(cache, now=lambda: 9_999, post=post), "fresh")
        self.assertEqual(calls[0]["grant_type"], "refresh_token")
        self.assertEqual(cache.written["refresh_token"], "r2")

    def test_missing_cache_raises_no_token(self):
        with self.assertRaises(m365.CliError) as ctx:
            m365.access_token(FakeCache(None), now=lambda: 0, post=lambda *a: {})
        self.assertEqual(ctx.exception.code, "no_token")

    def test_failed_refresh_raises_rather_than_returning_empty(self):
        cache = FakeCache({"access_token": "stale", "refresh_token": "r", "expires_at": 0})
        with self.assertRaises(m365.CliError) as ctx:
            m365.access_token(cache, now=lambda: 1, post=lambda *a: {"error": "invalid_grant"})
        self.assertEqual(ctx.exception.code, "refresh_failed")


class TestCacheFile(unittest.TestCase):
    def test_write_then_read_round_trips_and_is_owner_only(self):
        with tempfile.TemporaryDirectory() as d:
            cache = m365.TokenCache(Path(d) / "token.json")
            cache.write({"access_token": "a", "refresh_token": "r", "expires_in": 3600})
            self.assertEqual(cache.read()["refresh_token"], "r")
            mode = stat.S_IMODE(os.stat(cache.path).st_mode)
            self.assertEqual(mode, 0o600, f"cache must be 0600, got {oct(mode)}")

    def test_clear_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            cache = m365.TokenCache(Path(d) / "token.json")
            cache.write({"access_token": "a", "expires_in": 1})
            self.assertTrue(cache.clear())
            self.assertFalse(cache.clear())


class TestGraphSeam(unittest.TestCase):
    def test_get_encodes_params_and_returns_body(self):
        seen = {}

        def transport(method, url, token, body=None):
            seen.update(method=method, url=url, token=token)
            return 200, {"value": [1, 2]}

        g = m365.Graph(lambda: "tok", transport)
        out = g.get("/me/messages", {"$top": 3, "$search": '"a b"'})
        self.assertEqual(seen["method"], "GET")
        self.assertEqual(seen["token"], "tok")
        # assert the parameters that arrived, not the encoding that carried them
        query = urllib.parse.parse_qs(urllib.parse.urlparse(seen["url"]).query)
        self.assertEqual(query["$top"], ["3"])
        self.assertEqual(query["$search"], ['"a b"'])
        self.assertEqual(out["value"], [1, 2])

    def test_http_error_becomes_clierror_with_the_graph_code(self):
        def transport(method, url, token, body=None):
            return 403, {"error": {"code": "ErrorAccessDenied", "message": "Access is denied."}}

        with self.assertRaises(m365.CliError) as ctx:
            m365.Graph(lambda: "tok", transport).get("/me/messages")
        self.assertEqual(ctx.exception.code, "ErrorAccessDenied")

    def test_search_parses_the_nested_hits_envelope(self):
        def transport(method, url, token, body=None):
            self.assertEqual(method, "POST")
            return 200, {"value": [{"hitsContainers": [{"hits": [{"hitId": "h1"}]}]}]}

        hits = m365.Graph(lambda: "tok", transport).search("chatMessage", "SOW", 5)
        self.assertEqual(hits, [{"hitId": "h1"}])

    def test_search_returns_empty_when_the_envelope_is_missing(self):
        g = m365.Graph(lambda: "tok", lambda *a, **k: (200, {"value": []}))
        self.assertEqual(g.search("chatMessage", "x", 5), [])


class TestOutputContract(unittest.TestCase):
    def test_error_envelope_is_machine_readable_and_carries_no_token(self):
        import io
        from contextlib import redirect_stdout

        def transport(method, url, token, body=None):
            return 403, {"error": {"code": "ErrorAccessDenied", "message": "Access is denied."}}

        real = m365.Graph
        m365.Graph = lambda *a, **k: real(lambda: "SECRET-TOKEN", transport)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = m365.main(["--json", "mail", "search", "x"])
        finally:
            m365.Graph = real
        payload = json.loads(buf.getvalue())
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "ErrorAccessDenied")
        self.assertNotIn("SECRET-TOKEN", buf.getvalue())


class TestTrimmers(unittest.TestCase):
    def test_message_trim_keeps_only_the_fields_an_agent_needs(self):
        out = m365._trim_message({
            "id": "1", "subject": "S", "from": {"emailAddress": {"address": "a@b.c"}},
            "receivedDateTime": "2026-01-01T00:00:00Z", "bodyPreview": "p" * 500, "isRead": False,
            "webLink": "u", "body": {"content": "should not appear"}})
        self.assertEqual(out["from"], "a@b.c")
        self.assertEqual(len(out["preview"]), 300)
        self.assertTrue(out["unread"])
        self.assertNotIn("body", out)

    def test_event_trim_flags_online_meetings(self):
        out = m365._trim_event({"id": "1", "subject": "S", "start": {"dateTime": "t"},
                                "end": {"dateTime": "u"}, "onlineMeeting": {"joinUrl": "x"}})
        self.assertTrue(out["online"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
