# Dictionary and permission boundaries

Use the installed dictionary as the source of terms. Use runtime checks as the source of actual behavior. A command being listed is necessary, not sufficient.

## What does discovery prove?

The helper reads `CFBundleIdentifier`, the version, and `OSAScriptingDefinition` from `Contents/Info.plist`. It first tries `/usr/bin/sdef APP`, then reads the declared resource in `Contents/Resources`. With no declared resource, it accepts a single `.sdef` there. It does not fetch replacement dictionaries from the internet or install Xcode.

`discover --full` returns class codes, property codes and access, elements, receiver declarations, command codes, and parameter codes. It merges class extensions. It does not expand external XML includes or infer inherited terminology. A dictionary that needs those features can need another adapter. Legacy `aete` resources can require a working `sdef` tool; `aete` is a resource format, not a required command-line tool.

The reported capabilities describe **this helper's recognized protocol**, not everything the browser might do. A browser can be scriptable but lack this adapter. The Chromium adapter requires application/window/tab containment, stable IDs, URL/title/loading, and the expected codes. It checks the `execute` parameter and tab receiver declaration separately. It checks URL access before advertising navigation.

| Term | Exact code | Meaning |
| --- | --- | --- |
| window | `cwin` | Standard window class |
| tab | `CrTb` | Chromium tab class |
| id | `ID  ` | Four bytes: I, D, space, space |
| URL | `URL ` | Four bytes: U, R, L, space |
| execute | `CrSuExJa` | Event class `CrSu`, event ID `ExJa` |
| javascript parameter | `JvSc` | JavaScript text |
| go forward | `CrSuFwd ` | Event ID includes a trailing space |

Never trim or lowercase codes. Do not copy the research shorthand `ID ` as a three-byte code. The installed Edge and Chrome dictionaries use two spaces after `ID`.

All browser control in `browser_ae.py` goes through JXA and `/usr/bin/osascript`, which send Apple Events. The Objective-C bridge reads running-process metadata through AppKit; it does not perform UI automation. Request data lives in a private temporary file and is removed after the call. The helper does not start a WebDriver server, extension, debugger port, or browser process.

## What about another browser?

For Edge, Chrome, Brave, and any fork: discover its actual bundle and match the dictionary, then probe the selected tab. Do not assume different channels share an ID or that a Brave build matches Chrome because both are Chromium-based.

For Safari or a different model: inspect `--full`. The local Safari dictionary defines `tab` as `bTab` and uses `do JavaScript` (`sfridojs`); that is not the Chromium protocol. Its tab definition does not advertise the stable tab ID used by this helper. Do not use a tab index as a silent substitute. Read-only metadata inspection may still be possible from its dictionary, but persistent concurrent mutation needs a separate, verified adapter. Ask before building it.

For a missing dictionary: report that Apple Events support could not be established for the installed app. Do not infer support or absence from the engine or brand alone. Request a manual step for unsupported operations. The AX inspector requires an existing native document binding and cannot replace a missing adapter. CDP, WebDriver, and Playwright remain outside this skill. `browser_ae.py` remains Apple Events-only. `browser_ax.py` uses public ApplicationServices AX APIs and requires the existing document binding plus verified foreground mapping. It does not supply a missing native adapter or bypass host/OS permissions. See [the AX guide](accessibility.md) for inspection commands and errors. AX writes are disabled with `AX_WRITES_DISABLED`, without an override.

The dictionary also lists commands such as save, print, bookmarks, editing, and generic object movement. They are outside the helper's tested command set. Save without an explicit destination can open a dialog; print can show browser UI. Clipboard editing competes with the user. Generic `move` must not be treated as a reliable tab-drag API. Inspect and test a separate implementation in an approved fixture before extending the helper.

## Which permission failed?

Keep these three layers separate:

1. **macOS Automation/TCC:** Does the responsible launcher have permission to control this browser? A normal send can trigger a consent prompt. The helper is not a no-prompt `AEDeterminePermissionToAutomateTarget` preflight.
2. **Packaged sender configuration:** A signed/hardened or sandboxed app can need a purpose string and the appropriate Apple Events entitlement or scripting-target permission. This is a sender-build issue, not a tab or selector issue.
3. **Browser JavaScript/policy:** Chromium has a separate JavaScript-from-Apple-Events switch. Current upstream code also checks whether developer tools are allowed for the profile. Native tab reads working does not prove `execute` is allowed.

For TCC denial, have the user review the Automation permission for their actual launcher and browser in System Settings. The responsible host can be affected by Ghostty, Herdr, a shell, or another process in the launch chain. Record the error and launcher context; do not guess which process owns the grant. A basic diagnostic is:

```bash
ps -o pid=,ppid=,comm= -p $$ -p "$PPID"
```

This shows a process context, not definitive TCC attribution. A script working in Script Editor does not prove it will work from another host. If Herdr inspection is needed, load the `herdr` skill before issuing its commands.

For the browser JS gate, ask the user to enable **View → Developer → Allow JavaScript from Apple Events** if that menu exists in the installed build. Then repeat the harmless probe on the selected ordinary page. If enterprise policy blocks it, stop and involve the owner. Never toggle the setting through UI scripting, edit browser preferences, change policy, reset TCC, or patch its database.

## How should errors be handled?

The CLI emits one JSON envelope for operation results and returns exit status 1 on an operation failure. Argument-parser usage errors use standard argparse output and exit status 2. Do not parse human-readable AppleScript lists as JSON.

| Code | Response |
| --- | --- |
| `TARGET_NOT_FOUND`, `TARGET_NOT_RUNNING` | Ask the user to locate or start the chosen browser; do not launch automatically |
| `TARGET_NOT_SCRIPTABLE`, `CAPABILITY_UNAVAILABLE`, `COMMAND_UNAVAILABLE` | Explain the exact dictionary/adapter/runtime gap |
| `APPLE_EVENT_NOT_AUTHORIZED` | TCC/Automation check; usually error `-1743` |
| `JAVASCRIPT_APPLE_EVENTS_DISABLED` | Ask for the browser's manual JS gate; do not confuse with TCC |
| `BROWSER_POLICY_BLOCKED`, `APPLE_EVENT_FAILED` | Keep the original error number and message; do not guess a cause from a generic/localized message |
| `BROWSER_CHANGED`, `BROWSER_RESTARTED` | Inspect the new app/session and bind only after review |
| `OBJECT_NOT_FOUND`, `TARGET_AMBIGUOUS` | Stop; no front tab, index, URL, or title substitution |
| `PAGE_CHANGED`, `DOCUMENT_NOT_BOUND` | Review the page; do not bypass the guard by editing target JSON |
| `PAGE_LOADING` | Bounded wait on an expected load; no write replay |
| `JAVASCRIPT_EXECUTION_FAILED` | Inspect the outcome; a body can partly mutate before throwing |
| `TIMEOUT`, `TRANSPORT_FAILED`, `REPLY_COERCION_FAILED` | Outcome can be unknown; do not resend a write automatically |
| `UNSUPPORTED_ASYNC`, `OUTPUT_TOO_LARGE` | Work may already have started; inspect before changing the script |
| `WRITE_NOT_ALLOWED`, `TARGET_FILE_EXISTS`, `INVALID_TARGET`, `INVALID_SELECTION` | Fix the caller input deliberately; never weaken safety checks |

Raw error text can depend on language and browser build. The helper keeps unknown cases as `APPLE_EVENT_FAILED`. A failed read/write envelope is not a rollback guarantee. The AX helper is inspection-only. Its CLI and native methods refuse AX writes before dispatch. Historical receipts do not prove business success. Its focused-app/window/control checks are separate native calls, not an atomic lock.
