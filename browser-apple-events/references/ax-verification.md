# Accessibility verification status

**Decision, 2026-09-09: drop AX writes.** Keep Apple Events and scoped AX inspection; use manual input for unreachable controls. Both the CLI and native write methods reject AX writes with `AX_WRITES_DISABLED`. There is no override flag. The live write runner is retired and the focus experiment was removed.

Two Exa research passes found no reproducible, version-applicable fix within the agreed constraints. This does not prove all browser AX actions fail. No further write experiments or ADO journey are planned. Historical ADO success does not validate this helper.

## What has run?

The offline suite currently passes 44 tests with no failures:

```bash
python3 -m unittest discover -s "$SKILL/tests" -p 'test_*.py' -v
```

This includes 13 Apple Events tests, 27 AX tests using a controllable boundary or real CoreFoundation text conversion, and 4 loopback fixture/retired-runner tests. The text-ID regression runs the real JXA resolver against a model; it is not a general rule about AppleScript numeric comparisons. The temporary fixture listeners and threads stopped after both normal and failure paths. Those 44 checks do not control a browser. No production API was called and no ADO repository file was changed for this work.

After Alex confirmed owner coordination and approved disposable windows on 2026-09-09, live Edge 152.0.4191.53 exposed the cross-origin controls, including name-only and description-only buttons, advertised actions, disabled state, and duplicate labels. The first four runs dispatched no AX writes. The foreground guard stopped two attempts; a later read-only check found Teams in front. This is not proof of controlled takeover timing or business success.

The system-wide `AXFocusedApplication` read returned `-25204` immediately despite AX trust. Raising its timeout did not help. The helper now explicitly checks AppKit's foreground PID and the bound application's AX focus attributes. Those reads and the scoped inspection worked. The underlying system-wide read failure remains unexplained.

Cleanup closed the first two test tabs and stopped all fixture servers. On the foreground failures it left tabs untouched. The last read-only inventory showed one remaining fixture tab, `1273183753` (`AX same-title fixture`), for Alex to close manually. This historical ID is not permission to create a new binding and close it automatically.

The fifth live run passed seven assertions: distinct origins; duplicate, disabled, and absent-target rejection; unchanged saved state after those rejections; unverified business status after the no-effect action; and unchanged saved state after that action. Both the no-effect and Submit `AXPress` calls returned. Submit failed independent SQLite readback: expected `Pending`, revision `2`; actual `New`, revision `1`. The runner did not replay it. Text entry and rejection were not reached. Cleanup closed this run's tab `1273183774` and stopped both servers. The earlier leftover tab was not inspected again. See `native-fixture-5.txt` in the workspace below.

Later diagnostics (runs 6-10) did not establish a fix. Run 9 observed the fixture's ready event but no click event after AXPress. Holding the client alive for one second did not change the outcome. The focus-before-press experiment never reached dispatch and proves nothing. Runs 6 and 10 left fixture tabs for manual cleanup on foreground failures. Their historical IDs were `1273183815` and `1273183866`; their current presence is unverified. All fixture servers stopped. Final skill cleanup deliberately did not touch the browser.

## Which requested cases are covered?

| Case | Historical proof | Not proven; no further work planned |
| --- | --- | --- |
| Different-origin iframe button | Live AXPress returned; independent readback caught failed Submit (`New`, revision 1) | Diagnose whether the click reached its handler and why the saved state did not change |
| Description-only and name-only | Model dispatches once; live Edge scoped inspection exposed both forms and advertised actions | Native dispatch and saved outcome |
| Duplicate, disabled, absent | Model and live fixture reject each; independent saved state stays unchanged | ADO-specific selectors remain untested |
| Changed tree after dialog | Model re-resolves a new scope; replacement during a handoff aborts | Browser dialog rendering and AX reference behavior |
| Rejection text and confirmation | Model keeps text entry separate from one confirmation; HTTP fixture saves a reason and revision | Native AXValue application commitment and one UI confirmation |
| Advertised action with no effect | Model and live helper report unverified; native fixture readback stays unchanged | This does not prove that a browser click event fired |
| Same-title decoys | Multiple AX root documents and changed native context are rejected in the model | Native same-title/same-URL tab and window mapping |
| Restart, closed tab, same-URL reload | Existing AE input checks and AX propagation of stale-binding failures pass | New helper on actual stale browser documents; actual restart is not simulated PID proof |
| Moved tabs | Same-ID native resolution remains in the AE transport; a containing-window change during handoff aborts in the model | Actual cross-window drag, still unverified |
| User focus changes | Model rejects changed focus before dispatch, including a foreign-process focused element | Human takeover and switch-away-and-back timing; no atomicity claim |
| Disabled or changed record before action | Model rejects late disabled state, record state, revision, and value conflicts | Native timing check in disposable pages |
| Write with lost reply | Model preserves unknown, does not repeat on inspection; existing receipt prevents reuse | Lost real AX reply and independent readback |
| Visible but uncommitted input | Model separates AXValue from business state; fixture server rejects empty reason | Native controlled-input behavior and ADO saved-field/revision readback |
| Cleanup | Servers stopped; three live failure paths closed owned tabs, two foreground failures left tabs for the user | Manual closure of the remaining tab; successful journey cleanup |

These are contract checks, not an end-to-end pass. Model-only write and receipt tests remain as historical regression evidence. New checks prove that the CLI, native write methods, and retired live runner refuse writes even with approval flags. `tests/live_ax_check.py` no longer starts a browser or servers.

## What did the ADO evidence establish?

Read-only inspection used the supplied temporary helpers and `ado-restructuring` evidence dated 2026-09-09. The temporary AX helper had hardcoded targeting, title-substring window matching, broad tree reads, first-match controls, and focus-then-Space without a final focus check. Do not reuse it.

Saved rejection evidence recorded the ITCC/source result and revisions, while later submit output established only dispatch/readiness and an unresolved outcome. The D06 server-rule export proof is not browser submission proof. Historical journeys listed business actions; they did **not** provide a complete advertised AX action list.

Evidence pointers on the source Mac:

- `/tmp/it-ax.applescript`, `/tmp/it-board-ui.py`, `/tmp/d06-buttons.txt`, `/tmp/d06-submit-text.txt`
- `/Users/alexandrecastro/Developer/ado-restructuring/docs/ITCC-TEST-LEDGER.md`
- `information-technology/evidence/it-states-v2-ui-2026-09-09/request-rejection-255270.json`
- `information-technology/evidence/it-states-v2-ui-2026-09-09/normal-submission-readiness-defect.json`

No saved ID is a current binding. No signed iframe URL or broad AX dump was copied into this skill.

## What happens next?

1. Use the supported Apple Events path. Use AX only for scoped inspection of an already-foreground bound document.
2. Request manual clicks or text entry for unreachable controls, then verify saved fields and revisions.
3. Leave AX write work stopped. Reopening it requires a new user decision and concrete evidence, not another permission prompt or speculative workaround.

Research: [Chromium's asynchronous action contract](https://chromium.googlesource.com/chromium/src/+/main/docs/accessibility/browser/how_a11y_works_3.md), [AXSwift's same native call](https://github.com/tmandry/AXSwift/blob/main/Sources/UIElement.swift), and [Chrome sidebar example, not web-content proof](https://github.com/saqibameen/chrome-sidebar-toggle). Full research outputs and exact passages are in `exa-final-research.json` and `exa-final-primary-passages.json` in the workspace below.

Implementation and docs received an inline review and a separate read-only safety audit. No agent-trigger benchmark or old/new model comparison was run. The pre-edit snapshot and check artifacts live under `.skill-workspace/browser-apple-events/ax-iteration-1/` in the skills repository.
