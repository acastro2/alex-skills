"""Offline regression checks. Authentication and network connections are blocked.

Run with SHAREPOINT_HELPER_DIR to check another installed helper directory.
"""

import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

import requests


ROOT = Path(os.environ.get("SHAREPOINT_HELPER_DIR", Path(__file__).parent)).resolve()
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
import sharepoint_api as sp


def response(data):
    result = requests.Response()
    result.status_code = 200
    result._content = json.dumps(data).encode()
    return result


class DraftOnlyTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")))
        self.enterContext(patch.object(sp, "load_cookies", side_effect=AssertionError("Authentication forbidden")))
        self.enterContext(patch.dict(os.environ, {"SHAREPOINT_SITE_URL": "https://example.invalid/sites/Test"}))
        self.enterContext(patch.object(sp, "SITE_URL", "https://example.invalid/sites/Test"))
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.canvas = Path(self.temp) / "canvas.json"
        self.canvas.write_text('[{"controlType":4,"innerHTML":"<p>Local fixture</p>"}]')

    def run_stage(self, *extra):
        argv = ["stage_news_recap.py", "--id", "1", "--canvas", str(self.canvas),
                "--title", "Local fixture", "--date", "2026-09-17", *extra]
        with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(ROOT / "stage_news_recap.py"), run_name="__main__")

    def test_publish_flag_is_rejected_before_authentication(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as failure:
            self.run_stage("--publish", "--dry-run")
        self.assertEqual(failure.exception.code, 2)

    def test_api_publish_command_is_rejected_before_authentication(self):
        with patch.object(sys, "argv", ["sharepoint_api.py", "publish", "1"]), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as failure:
            runpy.run_path(str(ROOT / "sharepoint_api.py"), run_name="__main__")
        self.assertEqual(failure.exception.code, 1)

    def test_dry_run_needs_no_authentication(self):
        self.run_stage("--kind", "ainews", "--dry-run")

    def test_staging_only_emits_minor_checkin_and_draft_metadata(self):
        session = Mock(spec=requests.Session)
        session.headers = {}
        page = {"d": {
            "Url": "/sites/Test/SitePages/local.aspx", "Title": "Local fixture",
            "CanvasContent1": self.canvas.read_text(), "PromotedState": 1,
            "FirstPublished": "0001-01-01T00:00:00Z", "IsPageCheckedOutToCurrentUser": False,
        }}
        # The script verifies the title region in a second GET with its own $select. One
        # fixed response cannot answer both, and that mismatch is what made this case red.
        layout = {"d": {"LayoutWebpartsContent": '[{"controlType":0}]'}}

        def get(url, **kwargs):
            return response(layout if "LayoutWebpartsContent" in url else page)

        session.get.side_effect = get

        def post(url, **kwargs):
            if url.endswith("/contextinfo"):
                return response({"d": {"GetContextWebInformation": {"FormDigestValue": "local"}}})
            if url.endswith("/ProcessQuery"):
                return response([{"ErrorInfo": None}])
            return response({"d": {}})

        session.post.side_effect = post
        with patch.object(sp, "make_session", return_value=session):
            self.run_stage()

        urls = [call.args[0].lower() for call in session.post.call_args_list]
        self.assertFalse(any("/publish" in url or "/approve" in url for url in urls))
        checkins = [url for url in urls if "/checkin(" in url]
        self.assertTrue(checkins)
        self.assertTrue(all("checkintype=0" in url for url in checkins))
        csom = [call for call in session.post.call_args_list if call.args[0].endswith("/ProcessQuery")]
        self.assertTrue(csom)
        ns = {"sp": "http://schemas.microsoft.com/sharepoint/clientquery/2009"}
        for call in csom:
            xml = ET.fromstring(call.kwargs["data"])
            fields = [tuple(p.text for p in method.findall("sp:Parameters/sp:Parameter", ns))
                      for method in xml.findall("sp:Actions/sp:Method", ns)
                      if method.attrib["Name"] == "SetFieldValue"]
            self.assertEqual(fields, [("PromotedState", "1")])

    def test_published_news_is_refused_without_writes(self):
        session = Mock(spec=requests.Session)
        session.get.return_value = response({"d": {"PromotedState": 2, "FirstPublished": "2026-09-17T12:00:00Z"}})
        with patch.object(sp, "make_session", return_value=session), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises((ValueError, SystemExit)):
                self.run_stage()
        session.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
