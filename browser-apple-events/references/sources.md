# Evidence and limits

Checked on 2026-09-09. The user's research supplied the starting source list. The claims below were checked against installed bundles, actual execution, or the linked primary source. Do not reuse the original research's session-local citation markers as evidence.

## What was checked locally?

| Target | Evidence | Limit |
| --- | --- | --- |
| macOS 26.5.2 (25F84) | `sw_vers`; `/usr/bin/osascript`; local `man osascript` | Permission UI and launcher attribution can vary |
| Edge 152.0.4191.53 | Installed SDEF; real integration checks in disposable local pages | Does not prove all sites, profiles, or policies |
| Chrome 152.0.7977.84 | Installed SDEF is byte-identical to this Edge SDEF | No Chrome runtime actions were authorized or tested |
| Brave | The helper accepts matching dictionaries without a browser-name allowlist | Not installed here; no local dictionary or runtime proof |
| Safari 26.5.2 | Installed Safari SDEF: `bTab`, `pURL`, `sfridojs`; no advertised tab ID matching the helper | Discovery only; no Safari adapter or runtime test |
| `sdef` | Tool exists but fails because the active developer directory is Command Line Tools, not full Xcode | Verified fallback reads the bundle's declared `.sdef` |

The shared Chrome/Edge SDEF SHA-256 was `cd0453c2e166a0b664f8ea1d1ac04b53a54eed14835569b6104a7823dbb950f2`. Both expose `execute` as `CrSuExJa`, parameter `JvSc`, and `id` as the four-byte `ID  ` code.

## Which sources matter?

| Source | What it supports |
| --- | --- |
| [Chromium scripting.sdef](https://chromium.googlesource.com/chromium/src.git/+/lkgr/chrome/browser/ui/cocoa/applescript/scripting.sdef) and installed `Contents/Resources/scripting.sdef` | Object/command terminology; installed file wins for the target build |
| [Current tab_applescript.mm](https://chromium.googlesource.com/chromium/src/+/HEAD/chrome/browser/ui/cocoa/applescript/tab_applescript.mm) | Session-derived tab IDs; URL setter; native handlers; main-frame `ExecuteJavaScriptInIsolatedWorld`; JavaScript and DevTools permission gates; asynchronous Apple Event reply conversion |
| [Apple WWDC19: Advances in macOS Security](https://developer.apple.com/videos/play/wwdc2019/701/) | Apple Events consent is distinct from synthetic input; `AEDeterminePermissionToAutomateTarget`; prompting can block the calling thread |
| [Apple Script Editor dictionary guide](https://support.apple.com/guide/script-editor/view-an-apps-scripting-dictionary-scpedt1126/mac) | Manual dictionary-inspection route |
| [Apple Scripting Bridge](https://developer.apple.com/documentation/scriptingbridge) | Native Apple Events client alternative; not implemented by this helper |
| [Apple sandboxing and automation, QA1888](https://developer.apple.com/library/archive/qa/qa1888/_index.html) | Sender-side sandbox considerations; not a CLI entitlement prescription |
| Local `man osascript` | JXA language selection, passing a script path and arguments, stdout/stderr behavior |
| [JXA Cookbook](https://github.com/JXA-Cookbook/JXA-Cookbook/wiki/Safari-and-Chrome), fetched through Context7 | Secondary examples for `tab.execute({javascript: ...})`; real Edge execution checked the actual boundary |

Exa Contents retrieved the WWDC19 passages. Its Chromium fetch timed out, so the Chromium handler was fetched directly. Context7 resolved `/jxa-cookbook/jxa-cookbook`; its examples were not treated as stronger evidence than the installed dictionary or runtime checks.

## What do the checks prove?

`tests/test_browser_ae.py` checks exact codes, dictionary mismatches, URL restrictions, private non-overwriting target files, invalid inputs, and separate error categories. Error-category tests use real JXA but synthetic errors; they do not trigger TCC denial or change browser settings.

`tests/live_check.py` exercises the real Python CLI, `osascript`, browser Apple Events, and local renderer. It tests a same-URL decoy while another tab/window is selected, field edits and click results, same-URL reload detection, stale process bindings, missing targets, reply limits, native commands, and cleanup. It also supplies stale selection snapshots with changed PID or launch time and checks that both bind and new-tab reject them without side effects. These tests do not restart the user's browser. No server is started.

Edge rejected the generic native tab move into a tab collection with `Handler only handles single objects`. A separate manual check followed the user's report that the source tab had been dragged. The write reached the original source tab, but its reported window ID had not changed. The cross-window assertion therefore failed; this is not proof of successful cross-window drag recovery. Both test tabs were closed. Stable-ID resolution across windows is implemented, but real cross-window drag recovery remains unverified.

No automated test proves that concurrent website or human actions are fully locked out. Native guards are not atomic. No trigger-selection benchmark or cross-host model comparison was run. Passing these checks is execution evidence, not proof that every agent will choose and follow this skill correctly.
