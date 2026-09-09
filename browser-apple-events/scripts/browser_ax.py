#!/usr/bin/env python3
"""Guarded foreground AX inspection. Live AX writes are disabled."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit

import browser_ae as ae
from ax_native import NativeAX

ATTRIBUTES = {"role": "AXRole", "name": "AXTitle", "description": "AXDescription",
              "identifier": "AXIdentifier", "value": "AXValue"}
ROLES = ("AXButton", "AXCheckBox", "AXTextArea", "AXTextField")


def fail(code, message):
    raise ae.BrowserError(code, message, outcome="not_started")


def validate_spec(spec, write=False):
    if not isinstance(spec, dict) or set(spec) - {"expected", "frame", "region", "context", "control", "expected_value"}:
        fail("INVALID_INPUT", "Unknown AX specification field.")
    expected = spec.get("expected")
    if not isinstance(expected, dict) or not all(isinstance(expected.get(k), str) and expected[k] for k in ("account", "record", "state")):
        fail("INVALID_INPUT", "Expected context must include exact account, record, and state strings.")
    context = spec.get("context")
    if not isinstance(context, list) or not 1 <= len(context) <= 4:
        fail("INVALID_INPUT", "Supply 1–4 exact AX record/context selectors within the chosen scope.")
    for selector in context + [spec.get("control")] + ([spec["region"]] if "region" in spec else []):
        if not isinstance(selector, dict) or not selector or set(selector) - set(ATTRIBUTES) - {"label"}:
            fail("INVALID_INPUT", "Selectors accept exact role/name/description/identifier/value or label.")
        if not isinstance(selector.get("role"), str) or not selector["role"]:
            fail("INVALID_INPUT", "Every selector needs an exact role.")
        if not all(isinstance(v, str) and 0 < len(v) <= 500 for v in selector.values()):
            fail("INVALID_INPUT", "Selector values must be short, nonempty strings.")
    control = spec["control"]
    if control["role"] not in ROLES or "value" in control:
        fail("AX_ACTION_UNSUPPORTED", "Only ordinary buttons, checkboxes, and text controls are supported.")
    if write and not set(control).intersection(("name", "description", "identifier", "label")):
        fail("INVALID_INPUT", "Writes need an exact semantic control label or identifier.")
    if any(len(selector) == 1 for selector in context):
        fail("INVALID_INPUT", "Context must identify a record, not just a role.")
    frame = spec.get("frame")
    if frame is not None:
        if not isinstance(frame, dict) or set(frame) != {"origin", "path"}:
            fail("INVALID_INPUT", "Frame scope requires exact origin and path, never a signed URL.")
        if not isinstance(frame["origin"], str):
            fail("INVALID_INPUT", "Frame origin must be a string.")
        try:
            parts = urlsplit(frame["origin"])
        except ValueError:
            fail("INVALID_INPUT", "Invalid frame origin.")
        if parts.scheme not in ("https", "http") or not parts.netloc or parts.username or parts.password or parts.path or parts.query or parts.fragment:
            fail("INVALID_INPUT", "Invalid frame origin.")
        if not isinstance(frame["path"], str) or not frame["path"].startswith("/") or "?" in frame["path"] or "#" in frame["path"]:
            fail("INVALID_INPUT", "Invalid frame path.")


def redact(value):
    if not isinstance(value, str):
        return value
    def safe_origin(match):
        try:
            url = urlsplit(match[0])
            return url.scheme + "://" + (url.hostname or "redacted") + "/[redacted]"
        except ValueError:
            return "[redacted URL]"
    return re.sub(r"https?://[^\s]+", safe_origin, value)[:500]


class Handoff:
    """The two injected boundaries are the native AX client and the guarded AE read."""

    def __init__(self, ax, guard, target, spec):
        self.ax, self.guard, self.target, self.spec = ax, guard, target, spec
        self.deadline = time.monotonic() + 45

    def check_time(self):
        if time.monotonic() > self.deadline:
            fail("AX_TIMEOUT", "Handoff deadline reached; no automatic retry.")

    def walk(self, root, *, stop_web=False):
        pending, visited = [(root, 0)], []
        while pending:
            self.check_time()
            element, depth = pending.pop()
            if len(visited) >= 600 or depth > 24:
                fail("AX_TREE_LIMIT", "Tree inspection is incomplete. Narrow the scope; do not use partial matches.")
            if any(self.ax.equal(element, previous) for previous in visited):
                fail("AX_TREE_CHANGED", "AX hierarchy repeats an element; cannot prove complete scope.")
            visited.append(element)
            role = self.ax.get(element, "AXRole", optional=False)
            yield element, role
            if stop_web and role == "AXWebArea":
                continue
            children = self.ax.children(element, 600 - len(visited) - len(pending))
            pending.extend((child, depth + 1) for child in reversed(children))

    def matches(self, element, selector):
        for key, value in selector.items():
            if key == "label":
                if value not in (self.ax.get(element, "AXTitle"), self.ax.get(element, "AXDescription")):
                    return False
            elif self.ax.get(element, ATTRIBUTES[key]) != value:
                return False
        return True

    def find(self, root, selector):
        return [node for node, role in self.walk(root)
                if role == selector["role"] and self.matches(node, selector)]

    def unique(self, elements):
        if len(elements) != 1:
            raise ae.BrowserError("AX_TARGET_MISSING" if not elements else "AX_AMBIGUOUS",
                                  "Expected exactly one scoped target; no first-match fallback.",
                                  count=len(elements), outcome="not_started")
        return elements[0]

    def focus(self):
        app, window, focused = self.ax.focus()
        if any(self.ax.pid(element) != self.target["session"]["pid"] for element in (app, window, focused)):
            fail("AX_FOCUS_CHANGED", "Global focus is not in the bound browser process.")
        if self.ax.get(window, "AXRole", optional=False) != "AXWindow" or self.ax.get(window, "AXSubrole", optional=False) != "AXStandardWindow":
            fail("AX_MAPPING_UNPROVEN", "Focused AX window is not a standard browser window.")
        if self.ax.get(window, "AXMinimized", optional=False) is not False:
            fail("AX_MAPPING_UNPROVEN", "Window must be unminimized.")
        modal = self.ax.get(window, "AXModal")
        if modal is True:
            fail("AX_MAPPING_UNPROVEN", "Modal browser windows are unsupported.")
        return window, focused

    def page(self, window):
        roots = []
        for node, role in self.walk(window, stop_web=True):
            if role in ("AXSheet", "AXDialog"):
                fail("AX_MAPPING_UNPROVEN", "Native sheet or dialog blocks the browser page mapping.")
            if role == "AXWebArea":
                roots.append(node)
        root = self.unique(roots)
        if self.ax.get(root, "AXURL", optional=False) != self.target["url"]:
            fail("PAGE_CHANGED", "AX document URL does not match the bound top-level page.")
        return root

    def scope(self, root):
        frame = self.spec.get("frame")
        if frame:
            frames = []
            for node, role in self.walk(root):
                if role != "AXWebArea" or self.ax.equal(node, root):
                    continue
                raw = self.ax.get(node, "AXURL")
                if not isinstance(raw, str):
                    continue
                url = urlsplit(raw)
                if f"{url.scheme}://{url.netloc}" == frame["origin"] and url.path == frame["path"]:
                    frames.append(node)
            root = self.unique(frames)
        if "region" in self.spec:
            root = self.unique(self.find(root, self.spec["region"]))
        for selector in self.spec["context"]:
            self.unique(self.find(root, selector))
        return root

    def observe(self):
        self.check_time()
        native = self.guard()
        if native.get("context") != self.spec["expected"]:
            fail("AX_CONTEXT_CHANGED", "Fresh account, record, state, or revision differs from the task precondition.")
        window, focused = self.focus()
        root = self.page(window)
        scope = self.scope(root)
        controls = self.find(scope, self.spec["control"])
        return {"native": native, "window": window, "focused": focused,
                "root": root, "scope": scope, "controls": controls}

    def same(self, before, after):
        if before["native"] != after["native"]:
            fail("AX_CONTEXT_CHANGED", "Native target or record changed during the handoff.")
        for key in ("window", "focused", "root", "scope"):
            if not self.ax.equal(before[key], after[key]):
                fail("AX_FOCUS_CHANGED", "Focus or AX document changed. No reacquisition or stale path replay.")

    def describe(self, node):
        return {"role": self.ax.get(node, "AXRole"),
                "name": redact(self.ax.get(node, "AXTitle")),
                "description": redact(self.ax.get(node, "AXDescription")),
                "identifier": redact(self.ax.get(node, "AXIdentifier")),
                "enabled": self.ax.get(node, "AXEnabled"),
                "actions": self.ax.actions(node),
                "value_settable": self.ax.settable(node, "AXValue")}

    def ready(self, node, action, value):
        if self.ax.pid(node) != self.target["session"]["pid"]:
            fail("AX_MAPPING_UNPROVEN", "Control belongs to a different process.")
        if self.ax.get(node, "AXEnabled", optional=False) is not True:
            fail("AX_CONTROL_DISABLED", "Control is disabled or its enabled state is unknown.")
        if self.ax.get(node, "AXSubrole") == "AXSecureTextField":
            fail("AX_ACTION_UNSUPPORTED", "Secure text fields are outside this tool.")
        role = self.ax.get(node, "AXRole", optional=False)
        if "expected_value" in self.spec and self.ax.get(node, "AXValue", optional=False) != self.spec["expected_value"]:
            fail("AX_VALUE_CHANGED", "Current control value differs; preserve the edit.")
        if action == "set-value":
            if role not in ("AXTextArea", "AXTextField") or "expected_value" not in self.spec or not isinstance(value, str) or len(value) > 4000:
                fail("INVALID_INPUT", "Text entry needs a normal text control, expected_value, and at most 4000 characters.")
            if not self.ax.settable(node, "AXValue"):
                fail("AX_ACTION_UNSUPPORTED", "AXValue is not advertised as writable; no keyboard fallback.")
        elif action == "AXPress":
            if role not in ("AXButton", "AXCheckBox") or action not in self.ax.actions(node):
                fail("AX_ACTION_UNSUPPORTED", "Control does not advertise the requested supported action.")
            if role == "AXCheckBox" and "expected_value" not in self.spec:
                fail("INVALID_INPUT", "Checkbox actions require expected_value to avoid an unintended toggle.")
        else:
            fail("AX_ACTION_UNSUPPORTED", "Only advertised AXPress and writable text AXValue are implemented.")

    def execute(self, action=None, value=None, before_dispatch=lambda: None):
        validate_spec(self.spec, write=action is not None)
        attempted = False
        try:
            before = self.observe()
            if action is None:
                if len(before["controls"]) > 20:
                    fail("AX_OUTPUT_LIMIT", "More than 20 controls match; narrow the selector.")
                result = [self.describe(node) for node in before["controls"]]
                if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > 12 * 1024:
                    fail("AX_OUTPUT_LIMIT", "Control summaries exceed 12 KiB. Narrow the selector.")
                self.same(before, self.observe())
                return {"status": "inspected", "controls": result, "count": len(result)}
            node = self.unique(before["controls"])
            self.ready(node, action, value)
            after = self.observe()
            self.same(before, after)
            fresh = self.unique(after["controls"])
            if not self.ax.equal(node, fresh):
                fail("AX_TREE_CHANGED", "Control was replaced. Inspect again; no cached-path action.")
            self.ready(fresh, action, value)
            if self.guard() != after["native"]:
                fail("AX_CONTEXT_CHANGED", "Task context changed before dispatch.")
            window, focused = self.focus()
            if not self.ax.equal(window, after["window"]) or not self.ax.equal(focused, after["focused"]):
                fail("AX_FOCUS_CHANGED", "User focus changed before dispatch.")
            # Re-resolve ancestry and semantics after the final native round trip.
            root = self.page(window)
            scope = self.scope(root)
            final = self.unique(self.find(scope, self.spec["control"]))
            if not all(self.ax.equal(a, b) for a, b in ((root, after["root"]), (scope, after["scope"]), (final, fresh))):
                fail("AX_TREE_CHANGED", "AX document, scope, or control changed before dispatch.")
            before_dispatch()
            self.ready(final, action, value)
            last_window, last_focus = self.focus()
            if not self.ax.equal(window, last_window) or not self.ax.equal(focused, last_focus):
                fail("AX_FOCUS_CHANGED", "Focus changed during final control inspection.")
            self.check_time()
            attempted = True
            if action == "set-value":
                self.ax.set_value(final, value)
            else:
                self.ax.perform(final, action)
            return {"status": "action_dispatched", "action": action, "business_result": "unverified",
                    "verification": "Inspect the durable result without replaying this action."}
        except ae.BrowserError as exc:
            exc.error["outcome"] = "unknown" if attempted else "not_started"
            raise
        except Exception as exc:
            raise ae.BrowserError("AX_TRANSPORT_FAILED", "Unexpected AX failure. Inspect before retrying.",
                                  outcome="unknown" if attempted else "not_started") from exc


class Receipt:
    def __init__(self, path, fingerprint):
        try:
            self.fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            fail("AX_ATTEMPT_EXISTS", "This attempt already has a receipt. Inspect it and the record; do not replay.")
        self.base = {"schema": 1, "request_sha256": fingerprint}
        self.update({"status": "not_started"})

    def update(self, result):
        data = (json.dumps({**self.base, **result}, ensure_ascii=False) + "\n").encode()
        os.lseek(self.fd, 0, os.SEEK_SET)
        os.ftruncate(self.fd, 0)
        view = memoryview(data)
        while view:
            view = view[os.write(self.fd, view):]
        os.fsync(self.fd)

    def close(self):
        os.close(self.fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "act"))
    parser.add_argument("--target", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--guard-js", required=True, help="Reviewed read-only body returning exact account/record/state and optional revision")
    parser.add_argument("--action", choices=("AXPress", "set-value"))
    parser.add_argument("--text-file", help="Private UTF-8 file; not argv or clipboard")
    parser.add_argument("--receipt", help="New private attempt file; existing files block replay")
    parser.add_argument("--allow-write", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "act":
            fail("AX_WRITES_DISABLED", "AX writes were dropped after failed live verification. Use a manual click; no override flag.")
        target, spec = ae.read_json(args.target), ae.read_json(args.spec)
        ae.validate_target(target)
        if not target.get("document"):
            fail("DOCUMENT_NOT_BOUND", "AX needs the existing JavaScript document binding; no permission bypass.")
        validate_spec(spec)
        if args.command == "inspect" and (args.action or args.text_file or args.receipt or args.allow_write):
            fail("INVALID_INPUT", "Inspection cannot include action arguments.")
        code = Path(args.guard_js).read_text()
        if len(code.encode()) > ae.MAX_BYTES:
            fail("INVALID_INPUT", "Guard code exceeds 128 KiB.")
        manifest = ae.discover_app(target["browser"]["path"])
        if manifest["browser"] != target["browser"]:
            fail("BROWSER_CHANGED", "Installed browser differs from the binding.")
        ae.require_capability(manifest, "ax_context")
        request = {"operation": "ax-check", "browser": manifest["browser"], "target": target,
                   "limit": 4096, "code": code}
        with NativeAX() as ax:
            ax.start(target["session"]["pid"])
            handoff = Handoff(ax, lambda: ae.send(request), target, spec)
            result = handoff.execute()
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
        return 0
    except ae.BrowserError as exc:
        error = {**exc.error}
        error.setdefault("outcome", "not_started")
        error["message"] = redact(error["message"])
        print(json.dumps({"ok": False, "error": error}, ensure_ascii=False))
        return 1
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": {"code": "INVALID_INPUT", "message": "Cannot read inspection input.", "outcome": "not_started"}}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
