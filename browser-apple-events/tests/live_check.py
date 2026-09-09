#!/usr/bin/env python3
"""Opt-in integration check. Creates test windows; never closes pre-existing tabs."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

CLI = Path(__file__).resolve().parents[1] / "scripts/browser_ae.py"
PAGE = '''<!doctype html><meta charset="utf-8"><title>Apple Events disposable test</title>
<label>Name <input id="name" value=""></label>
<button id="add" onclick="document.querySelector('#count').textContent=String(Number(document.querySelector('#count').textContent)+1)">Add</button>
<output id="count">0</output><a href="https://example.com/">Example</a>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--allow-test-windows", action="store_true")
    args = parser.parse_args()
    if not args.allow_test_windows:
        parser.error("Get user approval, then pass --allow-test-windows.")
    app = str(Path(args.app).resolve())
    owned, passed = {}, []

    def jxa(source):
        result = subprocess.run(["/usr/bin/osascript", "-l", "JavaScript", "-"],
                                input="var app = Application(" + json.dumps(app) + ");\n" + source,
                                capture_output=True, text=True, timeout=20)
        if result.returncode:
            raise RuntimeError(result.stderr)
        return json.loads(result.stdout)

    def cli(*arguments, error=None):
        result = subprocess.run([sys.executable, str(CLI), *map(str, arguments)], capture_output=True, text=True, timeout=30)
        reply = json.loads(result.stdout)
        if error:
            assert result.returncode == 1 and reply["error"]["code"] == error, reply
            return reply
        assert result.returncode == 0 and reply["ok"], reply
        return reply["result"]

    def ok(name):
        passed.append(name)
        print("PASS " + name, flush=True)

    def tab_ref(row):
        return "app.windows.byId(" + json.dumps(row["window_id"]) + ").tabs.byId(" + json.dumps(row["tab_id"]) + ")"

    def state(row):
        return jxa("var t = " + tab_ref(row) + "; JSON.stringify({url:t.url(),loading:t.loading(),page:JSON.parse(t.execute({javascript:'JSON.stringify({name:document.querySelector(\"#name\")?.value,count:document.querySelector(\"#count\")?.textContent,origin:performance.timeOrigin})'}))});")

    def wait_for(row, url, previous_origin=None):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            value = state(row)
            if value["url"] == url and not value["loading"] and value["page"].get("count") is not None:
                if previous_origin is None or value["page"]["origin"] != previous_origin:
                    return value
            time.sleep(0.25)
        raise AssertionError("Test page did not become ready within 15 seconds")

    original_session = cli("tabs", "--app", app)["session"]
    with tempfile.TemporaryDirectory(prefix="browser-ae-live-") as directory:
        root = Path(directory)
        first, second = root / "first.html", root / "second.html"
        first.write_text(PAGE)
        second.write_text(PAGE.replace("disposable test", "second test"))
        first_url, second_url = first.as_uri(), second.as_uri()
        urls = [first_url, second_url]
        script_number = 0
        binding_number = 0
        selection_number = 0

        def select():
            nonlocal selection_number
            selection_number += 1
            path = root / f"selection-{selection_number}.json"
            cli("tabs", "--app", app, "--out", path)
            return path

        def run(target, body, mode="read", error=None):
            nonlocal script_number
            script_number += 1
            script = root / f"script-{script_number}.js"
            script.write_text(body)
            return cli("run", "--target", target, "--js-file", script, "--mode", mode, error=error)

        def bind(row, url=first_url, native=False):
            nonlocal binding_number
            binding_number += 1
            path = root / f"target-{binding_number}.json"
            extra = ["--native-only"] if native else []
            cli("bind", "--selection", select(), "--window-id", row["window_id"], "--tab-id", row["tab_id"],
                "--expect-url", url, "--out", path, *extra)
            return path

        def create_window():
            row = jxa("var w = app.Window().make(); var id = w.tabs.id()[0]; JSON.stringify({window_id:String(w.id()),tab_id:String(id),url:w.tabs.byId(id).url()});")
            owned[row["tab_id"]] = row["url"]
            jxa(tab_ref(row) + ".url = " + json.dumps(first_url) + "; JSON.stringify(true);")
            wait_for(row, first_url)
            return row

        try:
            target_row, decoy_row = create_window(), create_window()
            target, decoy = bind(target_row), bind(decoy_row)
            original = state(target_row)
            ok("real dictionary, native IDs, JS probe, and private document binding")

            selection = select()
            for field in ("pid", "launched"):
                stale_selection = root / f"stale-selection-{field}.json"
                data = json.loads(selection.read_text())
                data["session"][field] += 1
                stale_selection.write_text(json.dumps(data))
                before = cli("tabs", "--app", app)["tabs"]
                rejected_binding = root / f"rejected-{field}.json"
                cli("bind", "--selection", stale_selection, "--window-id", target_row["window_id"],
                    "--tab-id", target_row["tab_id"], "--expect-url", first_url, "--out", rejected_binding,
                    error="BROWSER_RESTARTED")
                cli("new-tab", "--selection", stale_selection, "--window-id", decoy_row["window_id"],
                    "--url", second_url, "--allow-write", error="BROWSER_RESTARTED")
                after = cli("tabs", "--app", app)["tabs"]
                fixture_windows = {target_row["window_id"], decoy_row["window_id"]}
                assert {r["tab_id"] for r in before if r["window_id"] in fixture_windows} == {r["tab_id"] for r in after if r["window_id"] in fixture_windows}
                assert not rejected_binding.exists()
            ok("stale selection PID or launch time rejects bind and new-tab without side effects")

            created = cli("new-tab", "--selection", selection, "--window-id", decoy_row["window_id"], "--url", second_url, "--allow-write")
            owned[created["tab"]["tab_id"]] = second_url
            wait_for(created["tab"], second_url)
            ok("new-tab returns the created tab ID in the explicit window")

            jxa("var w=app.windows.byId(" + json.dumps(decoy_row["window_id"]) + "); w.index=1; w.activeTabIndex=2; JSON.stringify(true);")
            text = 'Alex "quotes" \\ Unicode ação $(no-shell) `literal`\nsecond line'
            body = "const input=document.querySelector('#name'); if(input.value!=='') throw new Error('USER_EDIT_CONFLICT'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input," + json.dumps(text) + "); input.dispatchEvent(new Event('input',{bubbles:true})); document.querySelector('#add').click(); return document.querySelector('#count').textContent;"
            result = run(target, body, "write")
            assert result["value"] == "1", result
            assert state(target_row)["page"]["name"] == text.replace("\n", ""), state(target_row)
            assert run(decoy, "return document.querySelector('#count').textContent;")["value"] == "0"
            ok("background DOM write ignores selected tab/window and leaves same-URL decoy unchanged")

            run(target, "return Promise.resolve(1);", error="UNSUPPORTED_ASYNC")
            run(target, "return 'x'.repeat(140000);", error="OUTPUT_TOO_LARGE")
            ok("Promise and oversized replies fail explicitly")

            stale = root / "stale-session.json"
            stale_data = json.loads(target.read_text())
            stale_data["session"]["pid"] += 1
            stale.write_text(json.dumps(stale_data))
            run(stale, "document.querySelector('#add').click();", "write", error="BROWSER_RESTARTED")
            assert state(target_row)["page"]["count"] == "1"
            ok("stale process binding cannot mutate the page")

            move = jxa("var moved=false, failure=null; try { app.move(" + tab_ref(target_row) + ",{to:app.windows.byId(" + json.dumps(decoy_row["window_id"]) + ").tabs}); moved=true; } catch(e) { failure=String(e); } JSON.stringify({moved:moved,error:failure});")
            inventory = cli("tabs", "--app", app)["tabs"]
            matches = [row for row in inventory if row["tab_id"] == target_row["tab_id"]]
            if not matches:
                run(target, "document.querySelector('#add').click();", "write", error="OBJECT_NOT_FOUND")
                ok("invalidated tab identity is rejected instead of matching a same-URL tab")
                print("UNVERIFIED human drag: native move invalidated identity. " + json.dumps(move), flush=True)
                target_row = create_window()
                target = bind(target_row)
                original = state(target_row)
            else:
                target_row = matches[0]
                assert run(target, "return document.querySelector('#count').textContent;")["value"] == "1"
                if target_row["window_id"] == decoy_row["window_id"]:
                    ok("binding follows the same tab ID after a cross-window move")
                else:
                    print("UNVERIFIED cross-window drag: native move rejected: " + str(move["error"]), flush=True)

            cli("native", "--target", target, "--action", "reload", "--allow-write")
            wait_for(target_row, first_url, original["page"]["origin"])
            run(target, "document.querySelector('#add').click();", "write", error="PAGE_CHANGED")
            assert state(target_row)["page"]["count"] == "0"
            ok("same-URL reload invalidates the old document before the write")
            target = bind(target_row)

            jxa(tab_ref(target_row) + ".execute({javascript:\"document.querySelector('#name').value='human edit'\"}); JSON.stringify(true);")
            run(target, body, "write", error="JAVASCRIPT_EXECUTION_FAILED")
            assert state(target_row)["page"]["name"] == "human edit"
            assert state(target_row)["page"]["count"] == "0"
            ok("action-specific field precondition preserves concurrent human edits")

            cli("native", "--target", target, "--action", "navigate", "--url", second_url, "--allow-write")
            wait_for(target_row, second_url)
            run(target, "document.querySelector('#add').click();", "write", error="PAGE_CHANGED")
            assert state(target_row)["page"]["count"] == "0"
            native_target = bind(target_row, second_url, native=True)
            run(native_target, "return 1;", error="DOCUMENT_NOT_BOUND")
            ok("URL change rejects stale writes; native-only binding cannot run page code")

            cli("native", "--target", native_target, "--action", "back", "--allow-write")
            wait_for(target_row, first_url)
            native_target = bind(target_row, first_url, native=True)
            cli("native", "--target", native_target, "--action", "forward", "--allow-write")
            wait_for(target_row, second_url)
            native_target = bind(target_row, second_url, native=True)
            cli("native", "--target", native_target, "--action", "stop", "--allow-write")
            ok("native navigation, back, forward, and stop address the exact tab")

            target = bind(target_row, second_url)
            cli("native", "--target", target, "--action", "close", "--allow-write")
            run(target, "document.querySelector('#add').click();", "write", error="OBJECT_NOT_FOUND")
            assert run(decoy, "return document.querySelector('#count').textContent;")["value"] == "0"
            ok("closed target never falls back to another tab")
        finally:
            current_session = cli("tabs", "--app", app)["session"]
            if current_session != original_session:
                cleanup = {"closed": [], "left_for_user": list(owned), "reason": "Browser session changed; no IDs reused for cleanup."}
            else:
                cleanup = jxa("var owned=" + json.dumps(owned) + ",urls=" + json.dumps(urls) + "; var closed=[],left=[]; app.windows.id().forEach(function(wid){var w=app.windows.byId(wid); w.tabs.id().forEach(function(tid){if(Object.prototype.hasOwnProperty.call(owned,String(tid))){var t=w.tabs.byId(tid);var u=t.url(); if(urls.indexOf(u)!==-1 || u===owned[String(tid)]){t.close();closed.push(String(tid));}else{left.push({window_id:String(wid),tab_id:String(tid)});}}});}); JSON.stringify({closed:closed,left_for_user:left});")
            print("CLEANUP " + json.dumps(cleanup), flush=True)
            if cleanup["left_for_user"]:
                print("User took over test tabs. They were NOT closed. Close the listed tab IDs yourself if no longer needed.", flush=True)
        print(json.dumps({"passed": len(passed), "checks": passed}), flush=True)


if __name__ == "__main__":
    main()
