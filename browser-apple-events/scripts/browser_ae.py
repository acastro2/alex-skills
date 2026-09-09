#!/usr/bin/env python3
"""Dictionary discovery and checked Apple Events for an already-running browser."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
MAX_BYTES = 128 * 1024


class BrowserError(Exception):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.error = {"code": code, "message": message, **details}


def parse_dictionary(xml):
    """Preserve exact terms and byte codes; do not guess fork compatibility."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise BrowserError("INVALID_DICTIONARY", str(exc)) from exc
    if root.tag != "dictionary":
        raise BrowserError("INVALID_DICTIONARY", "Expected an SDEF dictionary.")
    classes, commands = {}, {}
    for node in root.findall("./suite/class"):
        classes[node.get("name")] = {
            "code": node.get("code"),
            "properties": {p.get("name"): dict(p.attrib) for p in node.findall("property")},
            "elements": [p.get("type") for p in node.findall("element")],
            "responds_to": [p.get("command") for p in node.findall("responds-to")],
        }
    for node in root.findall("./suite/class-extension"):
        entry = classes.get(node.get("extends"))
        if entry:
            entry["properties"].update({p.get("name"): dict(p.attrib) for p in node.findall("property")})
            entry["elements"].extend(p.get("type") for p in node.findall("element"))
            entry["responds_to"].extend(p.get("command") for p in node.findall("responds-to"))
    for node in root.findall("./suite/command"):
        code = node.get("code", "")
        commands[node.get("name")] = {
            "code": code,
            "event_class": code[:4] if len(code) == 8 else None,
            "event_id": code[4:] if len(code) == 8 else None,
            "parameters": {p.get("name"): dict(p.attrib) for p in node.findall("parameter")},
        }

    def prop(cls, name, code):
        return classes.get(cls, {}).get("properties", {}).get(name, {}).get("code") == code

    def command(name, code):
        return commands.get(name, {}).get("code") == code

    native = (
        classes.get("application", {}).get("code") == "capp"
        and classes.get("window", {}).get("code") == "cwin"
        and classes.get("tab", {}).get("code") == "CrTb"
        and "window" in classes.get("application", {}).get("elements", [])
        and "tab" in classes.get("window", {}).get("elements", [])
        and prop("window", "id", "ID  ")
        and prop("tab", "id", "ID  ")
        and prop("tab", "URL", "URL ")
        and prop("tab", "title", "pnam")
        and prop("tab", "loading", "ldng")
    )
    receivers = classes.get("tab", {}).get("responds_to", [])
    writable_url = native and classes["tab"]["properties"]["URL"].get("access", "rw") != "r"
    caps = {"tabs": native, "navigate": writable_url}
    for operation, term, code in (
        ("execute", "execute", "CrSuExJa"), ("reload", "reload", "CrSuRlod"),
        ("back", "go back", "CrSuBack"), ("forward", "go forward", "CrSuFwd "),
        ("stop", "stop", "CrSustop"), ("close", "close", "coreclos"),
    ):
        caps[operation] = native and command(term, code) and term in receivers
    caps["execute"] = caps["execute"] and commands["execute"]["parameters"].get("javascript", {}).get("code") == "JvSc"
    caps["new_tab"] = bool(writable_url and command("make", "corecrel"))
    caps["ax_context"] = bool(caps["execute"] and prop("application", "frontmost", "pisf")
                              and prop("window", "index", "pidx")
                              and prop("window", "active tab", "acTa")
                              and prop("window", "visible", "pvis")
                              and prop("window", "minimized", "pmnd"))
    return {
        "adapter": "chromium" if native else None,
        "capabilities": caps,
        "classes": classes,
        "commands": commands,
        "note": "Helper capabilities, not complete browser support. A different dictionary needs an adapter. Permissions and runtime behavior need a live probe.",
    }


def discover_app(app_path):
    app = Path(app_path).expanduser().resolve()
    try:
        with (app / "Contents/Info.plist").open("rb") as stream:
            info = plistlib.load(stream)
    except (OSError, plistlib.InvalidFileException) as exc:
        raise BrowserError("TARGET_NOT_FOUND", f"Cannot read app bundle: {app}") from exc
    browser = {
        "path": str(app), "bundle_id": info.get("CFBundleIdentifier"),
        "version": info.get("CFBundleShortVersionString", "unknown"),
    }
    if not browser["bundle_id"]:
        raise BrowserError("TARGET_NOT_FOUND", "App has no bundle identifier.")
    xml, source, warning = None, None, None
    try:
        result = subprocess.run(["/usr/bin/sdef", str(app)], capture_output=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            xml, source = result.stdout, "sdef"
        else:
            warning = result.stderr.decode("utf-8", errors="replace").strip()[:1500]
    except (OSError, subprocess.TimeoutExpired) as exc:
        warning = str(exc)
    if xml is None:
        resources = app / "Contents/Resources"
        declared = info.get("OSAScriptingDefinition")
        candidates = [resources / declared] if declared else list(resources.glob("*.sdef"))
        if len(candidates) != 1 or not candidates[0].is_file():
            return {"browser": browser, "adapter": None, "capabilities": {},
                    "error": {"code": "TARGET_NOT_SCRIPTABLE", "message": "No extractable dictionary. Legacy metadata may require full Xcode."},
                    "discovery_warning": warning}
        source = str(candidates[0])
        xml = candidates[0].read_bytes()
    if len(xml) > 2 * 1024 * 1024:
        raise BrowserError("INVALID_DICTIONARY", "Dictionary exceeds 2 MiB.")
    browser["sdef_sha256"] = hashlib.sha256(xml).hexdigest()
    return {"browser": browser, "definition_source": source, "discovery_warning": warning,
            **parse_dictionary(xml)}


def discover_browsers():
    candidates = []
    for root in (Path("/Applications"), Path.home() / "Applications", Path("/System/Applications")):
        for app in sorted(root.glob("*.app")):
            try:
                with (app / "Contents/Info.plist").open("rb") as stream:
                    info = plistlib.load(stream)
                schemes = {scheme for row in info.get("CFBundleURLTypes", []) for scheme in row.get("CFBundleURLSchemes", [])}
                if {"http", "https"} & schemes:
                    candidates.append(discover_app(app))
            except (OSError, plistlib.InvalidFileException):
                continue
    return candidates


def require_capability(manifest, operation):
    if not manifest.get("capabilities", {}).get(operation):
        raise BrowserError("CAPABILITY_UNAVAILABLE", f"Installed dictionary does not match the helper's {operation} contract.",
                           adapter=manifest.get("adapter"))


def read_json(path):
    try:
        value = json.loads(Path(path).expanduser().read_text())
    except (OSError, ValueError) as exc:
        raise BrowserError("INVALID_INPUT", f"Cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise BrowserError("INVALID_INPUT", "Expected a JSON object.")
    return value


def valid_identity(value):
    browser, session = value["browser"], value["session"]
    return (
        value["schema"] == 1
        and all(isinstance(browser[k], str) and browser[k] for k in ("path", "bundle_id", "version", "sdef_sha256"))
        and type(session["pid"]) is int and session["pid"] > 0
        and type(session["launched"]) in (int, float) and math.isfinite(session["launched"])
    )


def validate_selection(selection):
    try:
        valid = valid_identity(selection) and isinstance(selection["tabs"], list)
        valid = valid and all(all(isinstance(row[k], str) and row[k] for k in ("window_id", "tab_id", "url")) for row in selection["tabs"])
        if not valid:
            raise ValueError("Invalid selection")
    except (ValueError, KeyError, TypeError):
        raise BrowserError("INVALID_SELECTION", "Use the private snapshot written by tabs --out. Do not hand-edit it.") from None


def validate_target(target):
    try:
        valid = valid_identity(target) and all(isinstance(target[k], str) and target[k] for k in ("window_id", "tab_id", "url"))
        document = target.get("document")
        if document is not None:
            valid = valid and document["url"] == target["url"] and isinstance(document["time_origin"], (int, float)) and math.isfinite(document["time_origin"])
        if not valid:
            raise ValueError("Invalid target")
    except (ValueError, KeyError, TypeError):
        raise BrowserError("INVALID_TARGET", "Invalid target file. Bind again; do not hand-edit it.") from None


def write_target(path, target):
    destination = Path(path).expanduser()
    try:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(target, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    except FileExistsError:
        raise BrowserError("TARGET_FILE_EXISTS", "Use a new filename. Existing selections and bindings are not overwritten.") from None


def send(request, timeout=20):
    """The only live-browser boundary. JSON travels in a private file, not shell code."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="browser-ae-") as directory:
        payload = Path(directory) / "request.json"
        payload.write_text(json.dumps(request, ensure_ascii=False))
        payload.chmod(0o600)
        try:
            result = subprocess.run(
                ["/usr/bin/osascript", "-l", "JavaScript", str(HERE / "transport.js"), str(payload)],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise BrowserError("TIMEOUT", "Apple Event timed out. Do not replay a write; inspect its outcome first.", outcome="unknown") from None
        except OSError as exc:
            raise BrowserError("TRANSPORT_UNAVAILABLE", str(exc)) from exc
    if result.returncode:
        raise BrowserError("TRANSPORT_FAILED", result.stderr.strip()[:1500], outcome="unknown")
    try:
        reply = json.loads(result.stdout)
        if not isinstance(reply, dict) or not isinstance(reply.get("ok"), bool):
            raise ValueError("Invalid envelope")
    except ValueError:
        raise BrowserError("REPLY_COERCION_FAILED", "Transport did not return a JSON envelope.", outcome="unknown") from None
    if not reply["ok"]:
        error = reply["error"]
        raise BrowserError(error["code"], error["message"], **{k: v for k, v in error.items() if k not in ("code", "message")})
    return reply["result"]


def allowed_url(value):
    parsed = urlsplit(value)
    if parsed.scheme in ("http", "https") and parsed.hostname and not parsed.username and not parsed.password:
        return value
    if parsed.scheme == "file" and parsed.path.startswith("/") and parsed.netloc in ("", "localhost"):
        return value
    if value == "about:blank":
        return value
    raise BrowserError("UNSUPPORTED_PAGE", "Use an explicit http(s), local file, or about:blank URL. No browser UI, credentials in URLs, or javascript: navigation.")


def execute(args):
    if args.command == "discover":
        result = discover_app(args.app) if args.app else discover_browsers()
        if not args.full:
            for row in result if isinstance(result, list) else [result]:
                row.pop("classes", None)
                row.pop("commands", None)
        return result

    target, selection = None, None
    if args.command in ("run", "native"):
        target = read_json(args.target)
        validate_target(target)
        identity = target
    elif args.command in ("bind", "new-tab"):
        selection = read_json(args.selection)
        validate_selection(selection)
        identity = selection
    else:
        identity = None
    manifest = discover_app(identity["browser"]["path"] if identity else args.app)
    if identity and manifest["browser"] != identity["browser"]:
        raise BrowserError("BROWSER_CHANGED", "App version, path, ID, or dictionary changed. Select again after review.")
    request = {"operation": args.command, "browser": manifest["browser"], "target": target, "limit": MAX_BYTES}
    require_capability(manifest, "tabs")
    if selection:
        request["selected_session"] = selection["session"]
        if not any(row["window_id"] == args.window_id for row in selection["tabs"]):
            raise BrowserError("INVALID_SELECTION", "Window was not in this selection snapshot.")

    if args.command == "bind":
        if not any(row["window_id"] == args.window_id and row["tab_id"] == args.tab_id and row["url"] == args.expect_url for row in selection["tabs"]):
            raise BrowserError("INVALID_SELECTION", "Tab, window, and expected URL must match the selection snapshot.")
        allowed_url(args.expect_url)
        if not args.native_only:
            require_capability(manifest, "execute")
        request.update(window_id=args.window_id, tab_id=args.tab_id, url=args.expect_url, native_only=args.native_only)
    elif args.command == "run":
        require_capability(manifest, "execute")
        if not target.get("document"):
            raise BrowserError("DOCUMENT_NOT_BOUND", "Bind with JavaScript enabled before running page code.")
        code = Path(args.js_file).expanduser().read_text()
        if len(code.encode("utf-8")) > MAX_BYTES:
            raise BrowserError("INVALID_INPUT", "JavaScript file exceeds 128 KiB.")
        request.update(code=code, mode=args.mode)
    elif args.command == "native":
        if not args.allow_write:
            raise BrowserError("WRITE_NOT_ALLOWED", "Native actions require --allow-write and user authority for the action.")
        require_capability(manifest, args.action)
        request["action"] = args.action
        if args.action == "navigate":
            if not args.url:
                raise BrowserError("INVALID_INPUT", "navigate requires --url.")
            request["url"] = allowed_url(args.url)
    elif args.command == "new-tab":
        if not args.allow_write:
            raise BrowserError("WRITE_NOT_ALLOWED", "Creating a tab requires --allow-write.")
        require_capability(manifest, "new_tab")
        request.update(window_id=args.window_id, url=allowed_url(args.url))

    result = send(request)
    if args.command == "tabs":
        result = {"schema": 1, "browser": manifest["browser"], **result}
        if args.out:
            write_target(args.out, result)
    if args.command == "bind":
        write_target(args.out, result)
        return {"target_file": str(Path(args.out).expanduser()), "target": result}
    return result


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    discover = commands.add_parser("discover", help="Inspect dictionaries without controlling or launching browsers")
    discover.add_argument("--app", help="Exact app bundle path; omit to scan common app folders")
    discover.add_argument("--full", action="store_true", help="Include exact classes, properties, command and parameter codes")
    tabs = commands.add_parser("tabs", help="List stable tab/window IDs without selecting anything")
    tabs.add_argument("--app", required=True)
    tabs.add_argument("--out", help="Write a private selection snapshot for bind/new-tab without overwriting")
    bind = commands.add_parser("bind", help="Bind a selected tab in the same browser session and document")
    bind.add_argument("--selection", required=True, help="Snapshot from tabs --out; carries the selection's browser session")
    bind.add_argument("--window-id", required=True)
    bind.add_argument("--tab-id", required=True)
    bind.add_argument("--expect-url", required=True)
    bind.add_argument("--out", required=True)
    bind.add_argument("--native-only", action="store_true", help="No execute probe; cannot use this binding for DOM code")
    run = commands.add_parser("run", help="Run a synchronous JS function body after in-page document checks")
    run.add_argument("--target", required=True)
    run.add_argument("--js-file", required=True)
    run.add_argument("--mode", choices=("read", "write"), required=True, help="Declares intent; read is NOT a JavaScript sandbox")
    native = commands.add_parser("native", help="Native actions have a non-atomic URL check; replies acknowledge dispatch, not completion")
    native.add_argument("--target", required=True)
    native.add_argument("--action", choices=("navigate", "reload", "back", "forward", "stop", "close"), required=True)
    native.add_argument("--url")
    native.add_argument("--allow-write", action="store_true")
    new = commands.add_parser("new-tab", help="Create in an explicit window; the browser may select it")
    new.add_argument("--selection", required=True, help="Snapshot from tabs --out; rejects selection from a restarted browser")
    new.add_argument("--window-id", required=True)
    new.add_argument("--url", required=True)
    new.add_argument("--allow-write", action="store_true")
    return result


def main():
    args = parser().parse_args()
    try:
        result = execute(args)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
        return 0
    except BrowserError as exc:
        print(json.dumps({"ok": False, "error": exc.error}, ensure_ascii=False))
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": {"code": "INVALID_INPUT", "message": str(exc)}}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
