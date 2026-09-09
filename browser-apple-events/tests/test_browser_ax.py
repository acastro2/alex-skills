"""Offline safety contracts using a controllable AX boundary, not browser proof."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from browser_ax import Handoff, Receipt, validate_spec, redact
from browser_ae import BrowserError
from ax_native import NativeAX, check_error


def node(role, *, children=None, actions=None, writable=False, **attributes):
    return {"attributes": {"AXRole": role, **attributes}, "children": children or [],
            "actions": actions or [], "writable": writable}


class FixtureAX:
    def __init__(self):
        self.button = node("AXButton", AXDescription="Submit change for approval", AXEnabled=True, actions=["AXPress"])
        self.text = node("AXTextArea", AXDescription="Rejection reason", AXEnabled=True, AXValue="", writable=True)
        self.confirm = node("AXButton", AXTitle="Confirm reject", AXEnabled=True, actions=["AXPress"])
        self.frame = node("AXWebArea", AXURL="http://localhost:9102/approval?sig=private-token",
                          children=[node("AXStaticText", AXValue="Record FIXTURE-1"), self.button, self.text, self.confirm])
        self.root = node("AXWebArea", AXURL="http://localhost:9101/ticket/1", children=[self.frame])
        self.window = node("AXWindow", AXSubrole="AXStandardWindow", AXMinimized=False, children=[self.root])
        self.app = node("AXApplication")
        self.focused = self.root
        self.context = {"account": "fixture", "record": "FIXTURE-1", "state": "New", "revision": 1}
        self.native = {"window_id": "42", "tab_id": "900", "context": self.context}
        self.target = {"session": {"pid": 123}, "url": self.root["attributes"]["AXURL"]}
        self.spec = {"expected": copy.deepcopy(self.context),
                     "frame": {"origin": "http://localhost:9102", "path": "/approval"},
                     "context": [{"role": "AXStaticText", "value": "Record FIXTURE-1"}],
                     "control": {"role": "AXButton", "label": "Submit change for approval"}}
        self.business = {"submissions": 0, "rejections": 0, "reason": ""}
        self.no_effect = False
        self.lose_reply = False
        self.on_guard = None
        self.guards = 0

    def guard(self):
        self.guards += 1
        if self.on_guard:
            self.on_guard(self.guards)
        return copy.deepcopy(self.native)

    def get(self, element, attribute, optional=True):
        value = element["attributes"].get(attribute)
        if value is None and not optional:
            raise BrowserError("AX_ATTRIBUTE_MISSING", "Required attribute missing")
        return value

    def children(self, element, limit):
        if len(element["children"]) > limit:
            raise BrowserError("AX_TREE_LIMIT", "Incomplete tree")
        return element["children"]

    def actions(self, element):
        return element["actions"]

    def settable(self, element, attribute):
        return element["writable"]

    def pid(self, element):
        return 123

    def equal(self, left, right):
        return left is right

    def focus(self):
        return self.app, self.window, self.focused

    def perform(self, element, action):
        if not self.no_effect:
            if element is self.button:
                self.business["submissions"] += 1
            elif element is self.confirm:
                self.business["rejections"] += 1
                self.business["reason"] = self.text["attributes"]["AXValue"]
        if self.lose_reply:
            raise BrowserError("AX_TIMEOUT", "Reply lost after write")

    def set_value(self, element, value):
        element["attributes"]["AXValue"] = value

    def handoff(self):
        return Handoff(self, self.guard, self.target, self.spec)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.ax = FixtureAX()

    def rejected(self, code):
        before = copy.deepcopy(self.ax.business)
        with self.assertRaises(BrowserError) as error:
            self.ax.handoff().execute("AXPress")
        self.assertEqual(error.exception.error["code"], code)
        self.assertEqual(error.exception.error["outcome"], "not_started")
        self.assertEqual(self.ax.business, before)

    def test_description_only_discovery_and_press_are_scoped_without_private_frame_url(self):
        result = self.ax.handoff().execute()
        self.assertIsNone(result["controls"][0]["name"])
        self.assertEqual(result["controls"][0]["actions"], ["AXPress"])
        self.assertNotIn("private-token", json.dumps(result))
        result = self.ax.handoff().execute("AXPress")
        self.assertEqual(self.ax.business["submissions"], 1)
        self.assertEqual(result["status"], "action_dispatched")
        self.assertEqual(result["business_result"], "unverified")

    def test_name_only_control_and_text_entry_need_separate_confirmation(self):
        self.ax.spec["control"] = {"role": "AXTextArea", "description": "Rejection reason"}
        self.ax.spec["expected_value"] = ""
        self.ax.handoff().execute("set-value", 'Validation only: ação "quoted"\nsecond line')
        self.assertEqual(self.ax.business["rejections"], 0)
        self.assertEqual(self.ax.business["reason"], "")
        self.ax.spec.pop("expected_value")
        self.ax.spec["control"] = {"role": "AXButton", "name": "Confirm reject"}
        self.ax.handoff().execute("AXPress")
        self.assertEqual(self.ax.business["rejections"], 1)
        self.assertEqual(self.ax.business["reason"], self.ax.text["attributes"]["AXValue"])

    def test_duplicate_disabled_absent_and_unsupported_controls_do_not_write(self):
        for code in ("AX_AMBIGUOUS", "AX_CONTROL_DISABLED", "AX_TARGET_MISSING", "AX_ACTION_UNSUPPORTED"):
            with self.subTest(code=code):
                self.setUp()
                if code == "AX_AMBIGUOUS":
                    self.ax.frame["children"].append(copy.deepcopy(self.ax.button))
                elif code == "AX_CONTROL_DISABLED":
                    self.ax.button["attributes"]["AXEnabled"] = False
                elif code == "AX_TARGET_MISSING":
                    self.ax.spec["control"]["label"] = "Submit for approval"
                else:
                    self.ax.button["actions"] = []
                self.rejected(code)

    def test_duplicate_editor_label_outside_bound_frame_does_not_expand_scope(self):
        self.ax.root["children"].append(copy.deepcopy(self.ax.button))
        self.ax.handoff().execute("AXPress")
        self.assertEqual(self.ax.business["submissions"], 1)

    def test_state_revision_focus_disabled_and_replaced_control_changes_abort(self):
        for change, code in (("state", "AX_CONTEXT_CHANGED"), ("revision", "AX_CONTEXT_CHANGED"),
                             ("focus", "AX_FOCUS_CHANGED"), ("disabled", "AX_CONTROL_DISABLED"),
                             ("replace", "AX_TREE_CHANGED"), ("window", "AX_CONTEXT_CHANGED")):
            for phase in (2, 3):
                with self.subTest(change=change, phase=phase):
                    self.setUp()
                    def change_on_guard(number):
                        if number != phase:
                            return
                        if change in ("state", "revision"):
                            self.ax.context[change] = "changed"
                        elif change == "focus":
                            self.ax.focused = self.ax.text
                        elif change == "disabled":
                            self.ax.button["attributes"]["AXEnabled"] = False
                        elif change == "replace":
                            self.ax.frame["children"][1] = copy.deepcopy(self.ax.button)
                        else:
                            self.ax.native["window_id"] = "43"
                    self.ax.on_guard = change_on_guard
                    self.rejected(code)

    def test_new_dialog_tree_is_found_on_next_operation_not_cached(self):
        self.ax.handoff().execute()
        self.ax.frame["children"] = [node("AXGroup", AXDescription="Reject dialog", children=self.ax.frame["children"])]
        self.ax.spec["region"] = {"role": "AXGroup", "description": "Reject dialog"}
        self.ax.spec["control"] = {"role": "AXButton", "name": "Confirm reject"}
        self.ax.handoff().execute("AXPress")
        self.assertEqual(self.ax.business["rejections"], 1)

    def test_cross_process_focused_element_stops_without_a_write(self):
        self.ax.pid = lambda element: 999 if element is self.ax.focused else 123
        self.rejected("AX_FOCUS_CHANGED")

    def test_focus_change_while_receipt_is_persisted_stops_before_dispatch(self):
        def persist_then_take_over():
            self.ax.focused = self.ax.text
        with self.assertRaises(BrowserError) as error:
            self.ax.handoff().execute("AXPress", before_dispatch=persist_then_take_over)
        self.assertEqual(error.exception.error["code"], "AX_FOCUS_CHANGED")
        self.assertEqual(error.exception.error["outcome"], "not_started")
        self.assertEqual(self.ax.business["submissions"], 0)

    def test_large_multibyte_summaries_are_rejected_before_output(self):
        self.ax.spec["control"] = {"role": "AXButton"}
        for _ in range(10):
            self.ax.frame["children"].append(node("AXButton", AXTitle="🧪" * 500, AXDescription="🧪" * 500, AXEnabled=True))
        with self.assertRaises(BrowserError) as error:
            self.ax.handoff().execute()
        self.assertEqual(error.exception.error["code"], "AX_OUTPUT_LIMIT")

    def test_native_binding_failures_are_not_ax_fallback_opportunities(self):
        for code in ("BROWSER_RESTARTED", "OBJECT_NOT_FOUND", "PAGE_CHANGED", "AX_FOCUS_REQUIRED", "APPLE_EVENT_NOT_AUTHORIZED"):
            with self.subTest(code=code):
                self.setUp()
                def reject(_):
                    raise BrowserError(code, "Bound target rejected")
                self.ax.on_guard = reject
                self.rejected(code)

    def test_same_title_same_url_decoy_page_and_native_sheet_reject_mapping(self):
        for kind, code in (("decoy", "AX_AMBIGUOUS"), ("sheet", "AX_MAPPING_UNPROVEN"), ("url", "PAGE_CHANGED")):
            with self.subTest(kind=kind):
                self.setUp()
                if kind == "decoy":
                    self.ax.window["children"].append(copy.deepcopy(self.ax.root))
                elif kind == "sheet":
                    self.ax.window["children"].append(node("AXSheet"))
                else:
                    self.ax.root["attributes"]["AXURL"] += "?changed"
                self.rejected(code)

    def test_missing_required_attribute_and_incomplete_scope_fail_closed(self):
        self.ax.window["attributes"].pop("AXMinimized")
        self.rejected("AX_ATTRIBUTE_MISSING")
        self.setUp()
        self.ax.frame["children"].extend(node("AXButton") for _ in range(601))
        self.rejected("AX_TREE_LIMIT")

    def test_context_from_another_ticket_cannot_match_by_label_alone(self):
        self.ax.frame["children"][0]["attributes"]["AXValue"] = "Record DECOY-2"
        self.rejected("AX_TARGET_MISSING")

    def test_advertised_action_with_no_effect_is_not_a_business_pass(self):
        self.ax.no_effect = True
        result = self.ax.handoff().execute("AXPress")
        self.assertEqual(result["business_result"], "unverified")
        self.assertEqual(self.ax.business["submissions"], 0)

    def test_lost_reply_preserves_unknown_and_read_does_not_repeat_write(self):
        self.ax.lose_reply = True
        with self.assertRaises(BrowserError) as error:
            self.ax.handoff().execute("AXPress")
        self.assertEqual(error.exception.error["outcome"], "unknown")
        self.ax.handoff().execute()
        self.assertEqual(self.ax.business["submissions"], 1)

    def test_user_text_edit_and_nonwritable_value_are_preserved(self):
        self.ax.spec["control"] = {"role": "AXTextArea", "label": "Rejection reason"}
        self.ax.spec["expected_value"] = ""
        for writable, value, code in ((True, "human edit", "AX_VALUE_CHANGED"), (False, "", "AX_ACTION_UNSUPPORTED")):
            with self.subTest(code=code):
                self.ax.text["writable"] = writable
                self.ax.text["attributes"]["AXValue"] = value
                with self.assertRaises(BrowserError) as error:
                    self.ax.handoff().execute("set-value", "replacement")
                self.assertEqual(error.exception.error["code"], code)
                self.assertEqual(self.ax.text["attributes"]["AXValue"], value)

    def test_checkbox_requires_observed_value_and_never_forces_disabled_control(self):
        self.ax.button["attributes"]["AXRole"] = "AXCheckBox"
        self.ax.button["attributes"]["AXValue"] = 0
        self.ax.spec["control"]["role"] = "AXCheckBox"
        self.rejected("INVALID_INPUT")
        self.ax.spec["expected_value"] = 1
        self.rejected("AX_VALUE_CHANGED")


class InputAndNativeTests(unittest.TestCase):
    def test_live_write_cli_refuses_even_with_authority_before_input_or_receipt_access(self):
        with tempfile.TemporaryDirectory() as root:
            receipt = Path(root) / "attempt.json"
            for action in ("AXPress", "set-value"):
                with self.subTest(action=action):
                    result = subprocess.run([sys.executable, str(SCRIPTS / "browser_ax.py"), "act",
                        "--target", "/missing-target", "--spec", "/missing-spec", "--guard-js", "/missing-guard",
                        "--action", action, "--allow-write", "--receipt", str(receipt)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(json.loads(result.stdout)["error"]["code"], "AX_WRITES_DISABLED")
                    self.assertEqual(json.loads(result.stdout)["error"]["outcome"], "not_started")
                    self.assertFalse(receipt.exists())

    def test_native_write_boundary_refuses_without_loading_frameworks_or_sending_events(self):
        native = NativeAX.__new__(NativeAX)
        for method, value in ((native.perform, "AXPress"), (native.set_value, "reason")):
            with self.subTest(method=method.__name__), self.assertRaises(BrowserError) as error:
                method(None, value)
            self.assertEqual(error.exception.error["code"], "AX_WRITES_DISABLED")
            self.assertEqual(error.exception.error["outcome"], "not_started")

    def test_receipt_is_private_and_blocks_same_attempt_after_lost_reply(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "attempt.json"
            receipt = Receipt(path, "request-fingerprint")
            receipt.update({"status": "outcome_unknown"})
            receipt.close()
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(BrowserError) as error:
                Receipt(path, "same-or-different-request")
            self.assertEqual(error.exception.error["code"], "AX_ATTEMPT_EXISTS")
            self.assertEqual(json.loads(path.read_text())["status"], "outcome_unknown")

    def test_invalid_cli_target_has_json_error_without_browser_access(self):
        with tempfile.TemporaryDirectory() as root:
            target, spec = Path(root) / "target.json", Path(root) / "spec.json"
            target.write_text('{}')
            spec.write_text('{}')
            result = subprocess.run([sys.executable, str(SCRIPTS / "browser_ax.py"), "inspect", "--target", str(target), "--spec", str(spec), "--guard-js", "/missing"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["error"]["code"], "INVALID_TARGET")

    def test_unknown_selector_keys_and_role_only_writes_are_rejected(self):
        for key in ("index", "contains", "coordinates", "keystroke"):
            spec = FixtureAX().spec
            spec["control"][key] = "1"
            with self.subTest(key=key), self.assertRaises(BrowserError):
                validate_spec(spec, write=True)
        spec = FixtureAX().spec
        spec["control"].pop("label")
        with self.assertRaises(BrowserError):
            validate_spec(spec, write=True)

    def test_invalid_origin_types_and_invalid_urls_fail_with_structured_input_error(self):
        for origin in (7, None, {}, "https://[broken", "https://user:password@example.com"):
            spec = FixtureAX().spec
            spec["frame"]["origin"] = origin
            with self.subTest(origin=origin), self.assertRaises(BrowserError) as error:
                validate_spec(spec)
            self.assertEqual(error.exception.error["code"], "INVALID_INPUT")

    def test_permission_errors_are_not_optional_missing_attributes(self):
        for code in (-25205, -25212):
            self.assertFalse(check_error(code, optional=True))
        for code, name in ((-25211, "AX_PERMISSION_DENIED"), (-25204, "AX_CANNOT_COMPLETE"), (-25202, "AX_TARGET_MISSING")):
            with self.subTest(code=code), self.assertRaises(BrowserError) as error:
                check_error(code, optional=True)
            self.assertEqual(error.exception.error["code"], name)

    def test_private_url_is_not_exposed_in_diagnostics(self):
        self.assertEqual(redact("Failed https://example.test/asset?sig=secret"), "Failed https://example.test/[redacted]")
        self.assertEqual(redact("Failed https://[bad?sig=secret"), "Failed [redacted URL]")

    @unittest.skipUnless(sys.platform == "darwin", "macOS CoreFoundation boundary")
    def test_native_focus_refuses_a_nonforeground_application_before_reading_its_controls(self):
        for frontmost in (False, None, 1, "true"):
            with self.subTest(frontmost=frontmost):
                native = NativeAX.__new__(NativeAX)
                native.application = object()
                def read_attribute(element, attribute, **kwargs):
                    if attribute != "AXFrontmost":
                        self.fail("Read controls from a browser that is not proven foreground.")
                    return frontmost
                native.get = read_attribute
                with self.assertRaises(BrowserError) as error:
                    native.focus()
                self.assertEqual(error.exception.error["code"], "AX_FOCUS_CHANGED")

    def test_real_corefoundation_string_roundtrip_without_browser_or_ax_permission(self):
        with NativeAX() as native:
            value = 'ação "quoted"\nsecond line 🧪'
            self.assertEqual(native.decode(native.string(value)), value)
            with self.assertRaises(BrowserError):
                native.string("do not truncate\x00this")


if __name__ == "__main__":
    unittest.main()
