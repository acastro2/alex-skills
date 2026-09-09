# Work beside the user, not instead of them

The user can change focus, type, drag tabs between windows, close windows, switch Spaces, or navigate while a task runs. No idle-time assumption makes those actions safe to ignore.

## What identifies the target?

Preserve the session from the moment of selection. `tabs --out` writes that snapshot; `bind` and `new-tab` require it. Checking only the current session when binding would miss a restart between selection and binding if the browser reused IDs.

Use the binding as a set of checks, not a saved UI pointer:

| Check | Why it exists | If it changes |
| --- | --- | --- |
| App path, bundle ID, version, dictionary hash | A fork or update can change the protocol | Inspect again; no blind reuse |
| Browser PID and launch time | Tab IDs are not durable across browser sessions | Stop and bind again after review |
| Tab ID, resolved across current window IDs | Focus and ordering can change; a tab can move | Follow only the same unique ID; missing means stop |
| Exact native URL and rendered `location.href` | A tab can navigate while remaining the same tab | Stop; inspect unexpected navigation |
| `performance.timeOrigin` | Reload can keep the URL but replace the document | Stop; inspect and bind the new document deliberately |
| Account, record key, control label, current field value | The same document can change underneath the agent | Stop the write on any conflict |

Binding by tab ID avoids a front-tab error. It does not prove the correct account, record, or action. Verify those from the page.

## How should an action run?

```mermaid
sequenceDiagram
    participant A as Agent
    participant B as Browser
    participant P as Bound document
    A->>B: Find same tab ID and check browser session
    A->>P: One execute call
    P->>P: Check URL and time origin
    P->>P: Check record and current field values
    P->>P: Perform one synchronous action
    P-->>A: Small JSON reply
    A->>P: Fresh read of task postcondition
```

Put all action checks before the first write. Do not do a read in one call, wait, then click from that old observation. Query the element again in the action call. Frameworks replace DOM nodes during rendering.

A synchronous renderer call reduces check-to-action races. It does not create a browser transaction. Event handlers can run synchronously during `.click()` or `dispatchEvent()`. Network responses, server state, browser navigation, and another process remain outside that call. A form submit can reach the server even if the Apple Event later times out.

Native commands have a larger gap: read and write are separate Apple Events. There is no compare-and-set URL command in the inspected Chromium dictionary. Do not describe native navigation or close as atomic. If the user and agent must mutate the exact same tab, ask for a separate task tab or a brief pause.

## What if the user changes something?

- **Focus or window order changes:** in the Apple Events path, keep going by ID. Do not activate the browser or restore the old arrangement. During an Accessibility action, stop if the user changes focus or target; do not compete with them.
- **Tab moves:** search current windows for the same tab ID, then recheck the page. A move that changes the ID ends the binding. Do not follow the title or URL instead.
- **Tab closes or browser restarts:** stop. Do not recreate the user's page, relaunch the browser, or select a lookalike.
- **Unexpected navigation or reload:** stop before a mutation. Rebinding is a decision, not error recovery. Do it only after confirming the new page still serves the user's task.
- **Expected navigation from your action:** wait with a deadline for the intended destination, inspect it, then make a fresh binding. A redirect can require fresh account and site checks.
- **Human edits the same field:** preserve their edit. Compare the current value with the value the task expects, not just the value observed long ago. If it differs, stop before changing any field.
- **Page is hidden or minimized:** ordinary DOM work may still work. Do not use `document.hidden` as a reason to steal focus. If the site needs foreground interaction, use the Accessibility handoff within the requested task, or ask for a manual step if it cannot safely reach the control. Do not assume an Accessibility action will satisfy every trusted-input requirement.

The document check does not catch every leave-and-return path, same-document navigation, or back-forward-cache restoration. Record and field preconditions still matter. A background request can also change server state without changing any local document marker.

## Accessibility handoff

Accessibility fallback and necessary brief focus changes have standing approval for the user's requested task. Do not ask again for transport or focus permission. A requested approval action or named batch can proceed without another confirmation. Ask only for missing business scope, ambiguous targets, or permissions that the host or OS requires; do not turn this into an open-ended approval loop.

1. State what Apple Events cannot reach and the exact intended effect, such as approving a named record through an iframe button. A cross-origin frame blocks the ordinary DOM route, but does not prove the control is exposed through Accessibility.
2. Keep the original browser session, tab, page, and record checks. Recheck them immediately before the UI action using Apple Events where available. If the binding is stale, stop and review; do not switch transports to ignore it.
3. Inspect the live Accessibility tree using a supported tool or a reviewed `System Events` script. Identify the browser process, window, displayed page, record context, and unique enabled control by its role/name/identifier. Do not assume Accessibility window indices equal Apple Event window IDs. If the mapping is ambiguous, request a manual click.
4. If the action needs foreground access, announce the brief focus change and proceed without another confirmation. Activate or select only the task's target. Recheck it after the focus change; stop if the user changes focus, tabs, windows, or the record during the handoff. Do not repeatedly take focus back.
5. Use the control's advertised Accessibility action. Reinspect before each action; do not replay cached tree paths after a layout change. Do not fall back to guessed coordinates, keyboard navigation sequences, or clipboard paste.
6. Verify the record's result through a fresh page, Accessibility, or authorized service read. An action returning is not proof of business approval. An uncertain result means stop and inspect, not click again.
7. Tell the user the handoff is over and return to Apple Events for supported work. Do not restore a stale desktop arrangement. Restore focus only if explicitly requested and no newer user choice would be overwritten.

Accessibility needs its own macOS authorization. Ask the user to grant it manually if needed. Do not automate security prompts, change browser policy, or use the fallback to work around an explicit permission denial. Use a reviewed Accessibility workaround by default when needed within the task; the bundled CLI does not implement or validate one. Never auto-approve or bypass mandatory harness/tool permission prompts. No real iframe approval button was tested by this policy change.

## How much should the agent do at once?

Read in small batches. Make one bounded write, then verify it. Do not run a ten-step form workflow inside one unreviewed script. Do not keep intervals, MutationObservers, event listeners, or browser-global workers running after a call.

Allow only one writing agent per tab. Coordinate ownership outside the browser before starting. A task directory or lock file is useful coordination, not exclusive control over a live page.

After a timeout, transport failure, exception, or missing reply, label the outcome **unknown**. Inspect the task's durable result. A visible success message or changed field may help; a server-side record is stronger for a submitted transaction. Never automatically replay a send, save, purchase, or delete.

## What should cleanup remove?

Record created tab IDs immediately. At cleanup, recheck the browser session, exact ID, and expected task page. Close only tabs still owned by the task. Do not close a reused user tab. If the user navigated a created tab elsewhere, leave it and say why. Do not restore old focus or layout; that would overwrite the user's newer choice.
