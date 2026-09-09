# Page operations through `execute`

These are function bodies for `browser_ae.py run --js-file`. Adapt selectors and expected values from a fresh, narrow read of the actual page. Never run an example against a logged-in site just to test the skill.

## Read a small page summary

```javascript
return {
  title: document.title,
  headings: Array.from(document.querySelectorAll('h1,h2')).slice(0, 12)
    .map(e => e.innerText.slice(0, 200)),
  controls: Array.from(document.querySelectorAll('button,input:not([type=password]),select,textarea'))
    .slice(0, 30).map(e => ({
      tag: e.tagName, id: e.id, name: e.getAttribute('name'),
      type: e.getAttribute('type'), label: e.getAttribute('aria-label'),
      text: e.tagName === 'BUTTON' ? e.innerText.slice(0, 120) : null,
      disabled: e.disabled
    }))
};
```

Do not dump all HTML or all input values. Hidden fields can contain secrets. Extract the few fields the user needs. Use explicit offsets and limits for large lists; include record keys so page reordering cannot silently change the meaning of a batch.

## Fill one text field without keyboard focus

First read the business record, field label, and current value. In the write call, check them again. This example checks an exact form field; add a record/account check for the real site before the setter.

```javascript
const matches = document.querySelectorAll('input[name="displayName"]');
if (matches.length !== 1) throw new Error('SELECTOR_NOT_UNIQUE');
const input = matches[0];
if (!['text', 'search', 'email', 'tel', 'url'].includes(input.type))
  throw new Error('UNSUPPORTED_INPUT_TYPE');
if (input.disabled || input.readOnly || input.getAttribute('aria-disabled') === 'true' ||
    input.closest('[inert]') || !input.getClientRects().length)
  throw new Error('CONTROL_NOT_READY');
if (input.value !== 'Expected current value') throw new Error('USER_EDIT_CONFLICT');

const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
setter.call(input, 'Requested new value');
input.dispatchEvent(new Event('input', {bubbles: true}));
input.dispatchEvent(new Event('change', {bubbles: true}));
return {value: input.value};
```

Generate string literals with JSON encoding, not manual quote replacement. The native setter is useful for ordinary inputs, but no recipe works with every framework. Verify the UI and business state with a fresh read. For a textarea use `HTMLTextAreaElement.prototype`; for a select validate the exact option exists and read back its value. For contenteditable, inspect the site's structure first. Do not overwrite `innerHTML` as a universal typing method.

Do not set password or file inputs with this generic recipe. Do not call `.focus()` or paste through the clipboard. Synthetic DOM events are not trusted keyboard events. If this DOM path cannot perform the required interaction, use the default Accessibility handoff in `shared-mac.md` within the requested task, or ask for a manual step if it cannot safely reach the control. Do not assume Accessibility can satisfy every trusted-input requirement.

## Click one verified control

A click can submit, delete, purchase, or publish. Check that the user's task authorizes that exact effect, not merely reading the page. Do not request duplicate confirmation for an already authorized action. A selector should match exactly one enabled, visible control inside the expected record.

```javascript
const matches = document.querySelectorAll('button[data-action="preview"]');
if (matches.length !== 1) throw new Error('SELECTOR_NOT_UNIQUE');
const button = matches[0];
if (button.innerText.trim() !== 'Preview') throw new Error('LABEL_CHANGED');
if (button.disabled || button.getAttribute('aria-disabled') === 'true' ||
    button.closest('[inert]') || !button.getClientRects().length)
  throw new Error('CONTROL_NOT_READY');
button.click();
return {dispatched: true};
```

Do not use positional selectors, the first partial-text match, cached DOM nodes, or screen coordinates. Geometry is only a readiness signal here, not a click target. It does not prove absence of overlays or correct business state. If `.click()` triggers a new tab or navigation, inspect the resulting IDs and destination before continuing.

For a submit, check the account, record, destination, and all relevant field values in the same call. Never bypass disabled controls or force a UI action through a hidden element. A `dispatched` reply is not proof the server accepted anything.

## Wait without holding the user's browser

Use a bounded host-side loop of **read-only** calls. Each read still uses the target guard. Example predicate file:

```javascript
const status = document.querySelector('[data-status="preview-ready"]');
return Boolean(status && status.getClientRects().length);
```

Check this predicate every 0.5 to 1 second for at most 15 seconds, using the host's monotonic clock. Stop early on true. Stop immediately on `PAGE_CHANGED`, `OBJECT_NOT_FOUND`, permission errors, or browser-session changes. On deadline, report what did not become ready. Do not keep retrying indefinitely and do not replay a write inside this loop.

After intended navigation, use native metadata reads to wait for the exact expected destination. An old document binding is supposed to fail. Inspect the new page and bind it once the navigation is understood. `loading=false` and `document.readyState='complete'` are not proof that a SPA has finished its work.

## Frames, shadow DOM, and async work

- The inspected Chromium handler executes in the main frame's isolated JavaScript world. DOM reads are the normal path; page-defined globals may not be available. Do not depend on React internals, framework stores, or a page's global API without testing.
- For a same-origin frame, select a unique iframe and verify its document URL and time origin **inside the action call**, in addition to the top-level guard. Selectors on `document` do not enter frames. Cross-origin frame DOM access is unavailable through ordinary page JavaScript. For its buttons, default to Accessibility within the user's requested task; no extra fallback approval is needed. Inspect whether the control is actually exposed and verify the record context; do not assume access or ask for manual clicks solely because the DOM route failed.
- Traverse open shadow roots explicitly and require unique matches at each step. Closed roots are unsupported. Do not claim a flat selector searches them.
- Promise results are unsupported by this helper. It detects a thenable only after the body ran, so an async side effect may already have started. Do not schedule background work and assume an error cancelled it.
- Do not use page-context `fetch` as an unreviewed backdoor to the site's API. It can use the logged-in account and change server state. Use a dedicated service skill where available, or get authority for the exact request and verify its result.
- Browser UI and native file pickers are not DOM controls. Explain the precise limitation and use Accessibility within the requested task where a control is exposed, or request a manual step if it cannot be reached safely. Login, passkeys, MFA, and security permission grants stay with the user. No hidden fallback and no CDP.
