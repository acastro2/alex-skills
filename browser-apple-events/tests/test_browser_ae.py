import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("browser_ae", SCRIPTS / "browser_ae.py")
ae = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ae)

DICTIONARY = '''<dictionary><suite name="Test" code="CrSu">
<class name="application" code="capp"><element type="window"/></class>
<class name="window" code="cwin"><element type="tab"/><property name="id" code="ID  " type="text" access="r"/></class>
<class name="tab" code="CrTb">
<property name="id" code="ID  " type="text" access="r"/>
<property name="URL" code="URL " type="text"/>
<property name="title" code="pnam" type="text" access="r"/>
<property name="loading" code="ldng" type="boolean" access="r"/>
<responds-to command="execute"/><responds-to command="go forward"/>
</class>
<command name="execute" code="CrSuExJa"><parameter name="javascript" code="JvSc" type="text"/></command>
<command name="go forward" code="CrSuFwd "/>
<command name="make" code="corecrel"/>
</suite></dictionary>'''


class DictionaryTests(unittest.TestCase):
    def test_supported_protocol_does_not_depend_on_browser_brand(self):
        result = ae.parse_dictionary(DICTIONARY)
        self.assertEqual(result["adapter"], "chromium")
        self.assertTrue(result["capabilities"]["execute"])
        self.assertTrue(result["capabilities"]["new_tab"])
        self.assertFalse(result["capabilities"]["reload"])

    def test_four_character_codes_keep_spaces_and_case(self):
        result = ae.parse_dictionary(DICTIONARY)
        self.assertEqual(result["commands"]["go forward"]["event_id"], "Fwd ")
        self.assertEqual(result["classes"]["tab"]["properties"]["id"]["code"], "ID  ")
        changed = ae.parse_dictionary(DICTIONARY.replace('code="JvSc"', 'code="jvsc"'))
        self.assertFalse(changed["capabilities"]["execute"])

    def test_generic_command_does_not_prove_tab_support(self):
        changed = DICTIONARY.replace('<responds-to command="execute"/>', '')
        self.assertFalse(ae.parse_dictionary(changed)["capabilities"]["execute"])

    def test_read_only_url_and_different_tab_models_fail_closed(self):
        readonly = DICTIONARY.replace('name="URL" code="URL " type="text"', 'name="URL" code="URL " type="text" access="r"')
        result = ae.parse_dictionary(readonly)
        self.assertTrue(result["capabilities"]["tabs"])
        self.assertFalse(result["capabilities"]["navigate"])
        alternate = ae.parse_dictionary(DICTIONARY.replace('code="CrTb"', 'code="bTab"'))
        self.assertIsNone(alternate["adapter"])
        self.assertFalse(any(alternate["capabilities"].values()))
        self.assertIn("execute", alternate["commands"])

    def test_invalid_dictionary_is_not_reported_as_supported(self):
        for xml in ("<dictionary>", "<html/>"):
            with self.subTest(xml=xml), self.assertRaises(ae.BrowserError) as error:
                ae.parse_dictionary(xml)
            self.assertEqual(error.exception.error["code"], "INVALID_DICTIONARY")


class InputTests(unittest.TestCase):
    def test_browser_ui_and_javascript_urls_are_rejected(self):
        for url in ("javascript:1+1", "edge://settings", "chrome-extension://id/", "data:text/html,x", "https://user:secret@example.com/"):
            with self.subTest(url=url), self.assertRaises(ae.BrowserError):
                ae.allowed_url(url)
        for url in ("https://example.com/", "http://localhost:8000/", "file:///tmp/page.html", "about:blank"):
            self.assertEqual(ae.allowed_url(url), url)

    def test_binding_is_private_and_never_overwrites_an_existing_binding(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "target.json"
            ae.write_target(path, {"tab_id": "42"})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ae.BrowserError):
                ae.write_target(path, {"tab_id": "99"})
            self.assertEqual(json.loads(path.read_text()), {"tab_id": "42"})

    def test_invalid_target_fails_before_any_browser_event_even_with_python_optimization(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "bad.json"
            path.write_text('{"schema":1}')
            result = subprocess.run([sys.executable, "-O", str(SCRIPTS / "browser_ae.py"), "native", "--target", str(path), "--action", "close", "--allow-write"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["error"]["code"], "INVALID_TARGET")

    def test_invalid_selection_is_rejected_before_tab_creation(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "bad-selection.json"
            path.write_text('{"schema":1,"tabs":[]}')
            result = subprocess.run([sys.executable, str(SCRIPTS / "browser_ae.py"), "new-tab", "--selection", str(path), "--window-id", "42", "--url", "https://example.com/", "--allow-write"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["error"]["code"], "INVALID_SELECTION")

    def test_missing_target_is_structured_failure(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "browser_ae.py"), "run", "--target", "/does-not-exist/target.json", "--mode", "write", "--js-file", "/does-not-exist/code.js"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["error"]["code"], "INVALID_INPUT")


@unittest.skipUnless(sys.platform == "darwin", "Requires macOS JXA; no browser access")
class TransportErrorTests(unittest.TestCase):
    def test_os_errors_remain_distinct_from_browser_javascript_gate(self):
        source = (SCRIPTS / "transport.js").read_text()
        cases = [{"number": -1743, "message": "Not authorized"}, {"number": -1712, "message": "Timed out"},
                 {"message": "Executing JavaScript through AppleScript is turned off. Turn on Allow JavaScript from Apple Events."},
                 {"number": -1728, "message": "Object missing"}]
        source += '\nfunction run() { return JSON.stringify(' + json.dumps(cases) + '.map(normalize)); }'
        result = subprocess.run(["/usr/bin/osascript", "-l", "JavaScript", "-"], input=source, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([r["code"] for r in json.loads(result.stdout)], ["APPLE_EVENT_NOT_AUTHORIZED", "TIMEOUT", "JAVASCRIPT_APPLE_EVENTS_DISABLED", "OBJECT_NOT_FOUND"])


if __name__ == "__main__":
    unittest.main()
