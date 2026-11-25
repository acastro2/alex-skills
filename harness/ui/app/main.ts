// The shell: top bar, left rail, routing, the live stream, passkey sign-in and the one action path.
import { act as runAction, ApiError, getJSON, passkeysSupported, registerPasskey, sessionInfo, signIn, signOut, type SessionInfo } from "./api.ts";
import type { Ctx, Route, Snapshot, UiState, UiViewId, ViewId, ViewName } from "./ctx.ts";
import { hashFor, parseHash, VIEWS, viewLabel } from "./ctx.ts";
import { clear, clock, h, icon, mmss, refreshTimes } from "./dom.ts";
import { askPermission, notifyChanges, permission } from "./notify.ts";
import { btn, skeleton } from "./parts.ts";
import { renderBundles } from "./views/bundles.ts";
import { renderChanges } from "./views/changes.ts";
import { renderDashboard } from "./views/dashboard.ts";
import { renderInbox } from "./views/inbox.ts";
import { emptyJournal, renderJournal } from "./views/journal.ts";
import { renderJobs } from "./views/jobs.ts";
import { renderMachine } from "./views/machine.ts";
import { onThemeChange, signals } from "./views/office.ts";
import { renderRules } from "./views/rules.ts";
import { renderSessions } from "./views/sessions.ts";
import { renderWorktrees } from "./views/worktrees.ts";

const $ = (id: string) => document.getElementById(id) as HTMLElement;
const appEl = $("app");
const topbar = $("topbar");
const rail = $("rail");
const main = $("main");
const statusEl = $("status");

const banner = h("div", { id: "banner", class: "banner-slot" });
const viewSlot = h("div", { id: "view-slot", class: "view-slot" });
main.append(banner, viewSlot);

const ui: UiState = { expanded: new Set(), drafts: new Map(), pending: new Set(), sent: new Set(), journal: emptyJournal(), pulse: null };

let snap: Snapshot | null = null;
let skew = 0;
let route: Route = parseHash(location.hash);
let info: (SessionInfo & { skew: number }) | null = null;
let gateMessage: string | null = null;
let gateBusy = false;
let loadError: string | null = null;
let ledgerError: string | null = null;
let lastUpdate: number | null = null;
let lastBeat = 0;
let stream: "connecting" | "live" | "dropped" = "connecting";
let source: EventSource | null = null;
let confirmOff = false;
let uiRev = 0;
let lastSig = "";
let deferred = false;
let scrolledFor = "";
let lastCtx: Ctx | null = null;

const now = () => Date.now() + skew;

// ---------------------------------------------------------------- status line

let statusTimer: ReturnType<typeof setTimeout> | null = null;
function say(text: string, tone: "ok" | "error" = "ok"): void {
  if (statusTimer) clearTimeout(statusTimer);
  clear(statusEl);
  statusEl.className = `status ${text ? `status-${tone} is-shown` : ""}`;
  if (!text) return;
  statusEl.append(h("span", null, text));
  if (tone === "error") statusEl.append(btn("Dismiss", { tone: "quiet", onClick: () => say("") }));
  if (tone === "ok") statusTimer = setTimeout(() => say(""), 6000);
}

// ---------------------------------------------------------------- context handed to views

function makeCtx(): Ctx | null {
  if (!snap) return null;
  const ctx: Ctx = {
    snap,
    route,
    now: now(),
    ui,
    go: (hash) => {
      if (location.hash === hash) paint(true);
      else location.hash = hash;
    },
    act,
    rerender: () => paint(true),
    toggle: (key) => {
      if (ui.expanded.has(key)) ui.expanded.delete(key);
      else ui.expanded.add(key);
      paint(true);
    },
  };
  lastCtx = ctx;
  return ctx;
}

async function act(key: string, action: string, args: Record<string, unknown>, done: string): Promise<boolean> {
  ui.pending.add(key);
  paint(true);
  try {
    const r = await runAction(action, args);
    say(typeof r.note === "string" ? r.note : done);
    return true;
  } catch (e) {
    const err = e as ApiError;
    if (err.status === 401 && err.code === "no-session") await endSession("Your session ended. Sign in again.");
    else say(err.status === 503 ? "The authority module is not available, so this action cannot run." : err.message, "error");
    return false;
  } finally {
    ui.pending.delete(key);
    paint(true);
  }
}

// ---------------------------------------------------------------- top bar and rail

const THEMES: { id: string; label: string; icon: string }[] = [
  { id: "system", label: "Auto", icon: "auto" },
  { id: "light", label: "Light", icon: "sun" },
  { id: "dark", label: "Dark", icon: "moon" },
];

let topSig = "";
let railSig = "";

function paintTopbar(): void {
  const gate = !info?.authenticated;
  const harnessOn = snap?.harness.on ?? true;
  const choice = window.harnessTheme?.choice() ?? "system";
  const perm = permission();
  // The bar is rebuilt only when something it shows changed, so a stream update never steals focus from it.
  const sig = JSON.stringify([gate, snap?.host, snap ? harnessOn : null, confirmOff, ui.pending.has("harness:toggle"), perm, choice, info?.until]);
  if (sig === topSig) return;
  topSig = sig;
  clear(topbar);

  topbar.append(
    h("a", { class: "brand", href: hashFor("office"), "aria-label": "harness, back to the dashboard" }, h("span", { class: "brand-mark", "aria-hidden": "true" }, "h"), h("span", { class: "brand-name" }, "harness")),
    h("span", { class: "host mono", title: "Host" }, snap?.host ?? location.hostname),
    h("span", { class: "spacer" }),
  );
  if (gate) {
    topbar.append(themeButton(choice));
    return;
  }

  const pending = ui.pending.has("harness:toggle");
  topbar.append(
    ...(snap
      ? [confirmOff && harnessOn
        ? h("span", { class: "confirm-off", role: "group", "aria-label": "Confirm switching the harness off" }, btn("Tap passkey to switch off", { tone: "danger", icon: "key", busy: pending, onClick: () => void toggleHarness() }), btn("Cancel", { tone: "quiet", onClick: () => { confirmOff = false; paintTopbar(); } }))
        : h(
            "button",
            { type: "button", class: `harness-state ${harnessOn ? "is-on" : "is-off"}`, disabled: pending, "aria-busy": pending ? "true" : undefined, title: harnessOn ? "Switch the harness off (needs a passkey tap)" : "Switch the harness on (needs a passkey tap)", onClick: () => { if (harnessOn) { confirmOff = true; paintTopbar(); (topbar.querySelector(".confirm-off button") as HTMLElement | null)?.focus(); } else void toggleHarness(); } },
            h("span", { class: "dot", "aria-hidden": "true" }),
            h("span", null, h("span", { class: "hide-narrow" }, "Harness "), harnessOn ? "on" : "off"),
            h("span", { class: "sr" }, harnessOn ? ". Switch off." : ". Switch on."),
          )]
      : []),
    h("span", { class: "timer mono", id: "timer", title: "Time left in the passkey session" }, h("span", { class: "timer-label" }, "Session "), h("span", { id: "timer-value" }, info ? mmss(info.until! - now()) : "")),
    h(
      "button",
      { type: "button", class: "icon-btn", disabled: perm === "granted" || perm === "denied" || perm === "unsupported", title: perm === "granted" ? "Notifications are on" : perm === "denied" ? "Notifications are blocked in the browser settings" : perm === "unsupported" ? "This browser has no notifications" : "Turn on silent notifications for new questions and stuck sessions", "aria-label": perm === "granted" ? "Notifications on" : perm === "denied" ? "Notifications blocked" : "Turn on notifications", onClick: async () => { await askPermission(); paintTopbar(); } },
      icon("bell", 16),
      h("span", { class: "btn-text" }, perm === "granted" ? "Notify on" : perm === "denied" ? "Blocked" : "Notify"),
    ),
    themeButton(choice),
    h("button", { type: "button", class: "icon-btn", "aria-label": "Sign out", title: "End the session", onClick: () => void endSession("Signed out.", true) }, icon("out", 16)),
  );
}

/** Three buttons, one per choice. Each label names what its click sets, and the current one is pressed. */
function themeButton(choice: string): HTMLElement {
  return h(
    "span",
    { class: "theme-seg", role: "group", "aria-label": "Theme" },
    THEMES.map((t) =>
      h(
        "button",
        {
          type: "button",
          class: "icon-btn",
          "data-theme-choice": t.id,
          "aria-pressed": String(choice === t.id),
          title: t.id === "system" ? "Follow the system theme" : `Use the ${t.label.toLowerCase()} theme`,
          onClick: () => {
            window.harnessTheme?.set(t.id);
            paintTopbar();
            topbar.querySelector<HTMLElement>(`[data-theme-choice="${t.id}"]`)?.focus({ preventScroll: true });
          },
        },
        icon(t.icon, 16),
        h("span", { class: "btn-text" }, t.label),
      ),
    ),
  );
}

async function toggleHarness(): Promise<void> {
  const on = snap?.harness.on ?? true;
  confirmOff = false;
  const ok = await act("harness:toggle", on ? "off" : "on", {}, on ? "The harness is off." : "The harness is on.");
  if (!ok) paintTopbar();
}

function paintRail(): void {
  const sig = JSON.stringify([info?.authenticated, route.view, snap?.counts, snap?.alerts]);
  if (sig === railSig) return;
  railSig = sig;
  clear(rail);
  if (!info?.authenticated) return;
  const item = (view: ViewName, label: string, ico: string, full?: string, count?: number, alert = 0) => {
    const current = route.view === view;
    // The amber number is what needs Alex. With nothing urgent the badge shows the plain count.
    const shown = alert > 0 ? alert : count;
    return h(
      "a",
      { class: `rail-item${current ? " is-current" : ""}`, href: hashFor(view), "aria-current": current ? "page" : undefined, title: full ?? label },
      icon(ico, 16),
      h("span", { class: "rail-label" }, label),
      shown !== undefined
        ? h("span", { class: `badge${alert > 0 ? " badge-alert" : ""}${shown === 0 ? " badge-zero" : ""}`, title: view === "journal" ? `${count} rows in the last hour` : alert > 0 ? `${alert} need you, ${count} in all` : `${count} in all` }, String(shown), h("span", { class: "sr" }, alert > 0 ? ` need you, ${count} in all` : view === "journal" ? " rows in the last hour" : " in all"))
        : null,
    );
  };
  rail.append(
    item("office", "Dashboard", "office"),
    ...VIEWS.map((v) => (v.id === "machine" ? item(v.id, v.short, "auto", v.label) : item(v.id, v.short, v.id, v.label, snap?.counts[v.id as ViewId], snap?.alerts[v.id as ViewId] ?? 0))),
  );
  // On a narrow screen the rail scrolls sideways: keep the current view in sight.
  const cur = rail.querySelector<HTMLElement>(".is-current");
  if (cur && rail.scrollWidth > rail.clientWidth) rail.scrollLeft = cur.offsetLeft - (rail.clientWidth - cur.offsetWidth) / 2;
}

function paintTitle(): void {
  const need = snap ? signals({ snap, route, now: now(), ui } as Ctx).filter((s) => s.tone === "amber").length : 0;
  document.title = `${need ? `(${need}) ` : ""}harness · ${viewLabel(route.view)}`;
}

// ---------------------------------------------------------------- banner (stale and error states)

function paintBanner(): void {
  clear(banner);
  const stale = info?.authenticated && (stream === "dropped" || (stream === "live" && now() - lastBeat > 15_000));
  if (ledgerError) {
    banner.append(
      h("div", { class: "banner banner-error", role: "alert" }, h("span", null, `The ledger cannot be read: ${ledgerError}. `, snap ? `Showing the last good data from ${clock(lastUpdate ?? now())}.` : ""), btn("Retry", { tone: "quiet", onClick: () => void loadSnapshot() })),
    );
  }
  if (stale) {
    banner.append(
      h("div", { class: "banner banner-stale", role: "status" }, h("span", null, `Live updates stopped. Last update ${lastUpdate ? clock(lastUpdate) : "never"}. Reconnecting.`), btn("Reconnect now", { tone: "quiet", onClick: connect })),
    );
  }
  viewSlot.classList.toggle("is-stale", Boolean(ledgerError || stale));
}

// ---------------------------------------------------------------- main view

const RENDER: Record<UiViewId, (ctx: Ctx) => HTMLElement> = {
  inbox: renderInbox,
  sessions: renderSessions,
  worktrees: renderWorktrees,
  bundles: renderBundles,
  rules: renderRules,
  journal: renderJournal,
  changes: renderChanges,
  jobs: renderJobs,
  machine: renderMachine,
};

function signature(): string {
  if (!snap) return `loading:${loadError ?? ""}`;
  const v = route.view;
  const base = `${v}|${route.id}|${JSON.stringify(route.q)}|${uiRev}|${ui.pending.size}|${ui.sent.size}|${ui.expanded.size}`;
  // The dashboard patches itself on each snapshot, so anything the snapshot carries is part of its signature.
  if (v === "office") return `${base}|${JSON.stringify([snap.seq, snap.counts, snap.alerts, snap.host, snap.harness, snap.views, snap.dash, snap.resources ?? null])}`;
  if (v === "journal") return `${base}|${JSON.stringify([snap.views.sessions.map((s) => s.id), snap.views.rules.map((r) => r.id)])}`;
  if (v === "machine") return `${base}|${JSON.stringify(snap.resources ?? null)}`;
  return `${base}|${JSON.stringify(snap.views[v])}`;
}

interface FocusKey {
  id: string;
  tag: string;
  label: string;
  text: string;
  start: number | null;
  end: number | null;
}

function focusKey(): FocusKey | null {
  const el = document.activeElement as HTMLElement | null;
  if (!el || !main.contains(el) || el === main) return null;
  const input = el as HTMLInputElement;
  return {
    id: el.id,
    tag: el.tagName,
    label: el.getAttribute("aria-label") ?? "",
    text: el.textContent?.trim().slice(0, 60) ?? "",
    start: typeof input.selectionStart === "number" ? input.selectionStart : null,
    end: typeof input.selectionEnd === "number" ? input.selectionEnd : null,
  };
}

function restoreFocus(k: FocusKey | null): void {
  if (!k) return;
  let target: HTMLElement | null = k.id ? document.getElementById(k.id) : null;
  if (!target) {
    const same = [...viewSlot.querySelectorAll<HTMLElement>(k.tag.toLowerCase())];
    target = same.find((e) => k.label && e.getAttribute("aria-label") === k.label) ?? same.find((e) => !k.label && e.textContent?.trim().slice(0, 60) === k.text) ?? null;
  }
  if (!target) return;
  target.focus({ preventScroll: true });
  const input = target as HTMLInputElement;
  if (k.start !== null && typeof input.setSelectionRange === "function") {
    try {
      input.setSelectionRange(k.start, k.end ?? k.start);
    } catch {
      /* input types without selection */
    }
  }
}

function paint(force = false): void {
  paintBanner();
  paintTitle();
  const sig = signature();
  if (!force && sig === lastSig) return;
  const active = document.activeElement as HTMLElement | null;
  if (!force && active && viewSlot.contains(active) && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName)) {
    deferred = true;
    return;
  }
  deferred = false;
  lastSig = sig;
  const focus = focusKey();
  ui.pulse = null;

  let view: HTMLElement;
  const ctx = makeCtx();
  if (!ctx) view = loadingView();
  else if (route.view === "office") view = renderDashboard(ctx);
  else view = RENDER[route.view](ctx);
  main.classList.toggle("is-dash", route.view === "office");
  // The dashboard root persists between paints: keep it where it is, so its scroll positions and focus stay.
  if (view.parentElement !== viewSlot || viewSlot.childElementCount !== 1) viewSlot.replaceChildren(view);
  refreshTimes(viewSlot, now());
  restoreFocus(focus);

  const where = `${route.view}/${route.id ?? ""}`;
  if (scrolledFor !== where && snap) {
    scrolledFor = where;
    const target = viewSlot.querySelector("[data-selected]");
    if (target) target.scrollIntoView({ block: "center" });
    else window.scrollTo({ top: 0 });
  }
}

function loadingView(): HTMLElement {
  const label = viewLabel(route.view);
  if (loadError) {
    return h("section", { class: "view" }, h("header", { class: "view-head" }, h("div", { class: "view-title" }, h("h1", { id: "view-h" }, label))), h("div", { class: "empty" }, h("p", { class: "empty-title" }, "The ledger cannot be read."), h("p", { class: "empty-why" }, loadError), btn("Try again", { onClick: () => void loadSnapshot() })));
  }
  return h("section", { class: "view", "aria-busy": "true" }, h("header", { class: "view-head" }, h("div", { class: "view-title" }, h("h1", { id: "view-h" }, label))), skeleton(route.view === "office" ? 3 : 6));
}

main.addEventListener("focusout", () => {
  if (!deferred) return;
  setTimeout(() => {
    const a = document.activeElement as HTMLElement | null;
    if (!a || !viewSlot.contains(a) || !/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)) paint(true);
  }, 0);
});

// ---------------------------------------------------------------- gate (register or sign in)

function paintGate(): void {
  appEl.classList.add("is-gate");
  paintTopbar();
  paintRail();
  clear(banner);
  const registered = info?.registered ?? true;
  const supported = passkeysSupported();
  const run = async () => {
    gateBusy = true;
    gateMessage = null;
    paintGate();
    try {
      if (registered) await signIn();
      else await registerPasskey();
      await start();
      return;
    } catch (e) {
      const err = e as Error;
      gateMessage = err.name === "NotAllowedError" ? "The passkey prompt was cancelled. Try again." : err.message;
    }
    gateBusy = false;
    paintGate();
  };
  viewSlot.classList.remove("is-stale");
  viewSlot.replaceChildren(
    h(
      "section",
      { class: "gate plate" },
      h("h1", { id: "view-h" }, registered ? "Sign in to harness" : "Register a passkey"),
      h("p", { class: "gate-text" }, registered ? "Use your passkey to open the page. The session stays open while you use it, up to 7 days, and survives restarts. Actions that change things ask for a fresh tap." : "No passkey is registered yet. Register one, in 1Password so every host shares it."),
      supported ? null : h("p", { class: "inline-error", role: "alert" }, "This browser has no passkey support. Open the page in Edge or Chrome, as localhost."),
      gateMessage ? h("p", { class: "inline-error", role: "alert" }, gateMessage) : null,
      btn(registered ? "Sign in with passkey" : "Register passkey", { tone: "primary", icon: "key", busy: gateBusy, disabled: !supported, onClick: () => void run() }),
    ),
  );
  const first = viewSlot.querySelector<HTMLElement>("button");
  first?.focus({ preventScroll: true });
}

async function endSession(message: string, callServer = false): Promise<void> {
  if (callServer) await signOut().catch(() => undefined);
  stopStream();
  snap = null;
  lastSig = "";
  info = { ...(info ?? { registered: true, now: Date.now(), session_ms: 0 }), registered: true, authenticated: false, until: null, skew: 0 };
  gateMessage = message;
  gateBusy = false;
  paintGate();
}

// ---------------------------------------------------------------- data and live stream

function accept(next: Snapshot): void {
  skew = next.at - Date.now();
  snap = next;
  loadError = null;
  ledgerError = null;
  lastUpdate = next.at;
  lastBeat = now();
  notifyChanges(next, (hash) => {
    location.hash = hash;
  });
  paintRail();
  paintTopbar();
  ui.pulse?.(next);
  paint();
  if (route.view === "office" && lastCtx) onThemeChange(makeCtx());
}

async function loadSnapshot(): Promise<void> {
  try {
    accept(await getJSON<Snapshot>("/api/snapshot"));
  } catch (e) {
    const err = e as ApiError;
    if (err.status === 401) return endSession("Your session ended. Sign in again.");
    if (snap) ledgerError = err.message;
    else loadError = err.message;
    paint(true);
  }
}

function stopStream(): void {
  source?.close();
  source = null;
}

function connect(): void {
  stopStream();
  stream = "connecting";
  source = new EventSource("/api/events");
  source.onopen = () => {
    stream = "live";
    lastBeat = now();
    paintBanner();
  };
  source.addEventListener("snapshot", (e) => {
    stream = "live";
    try {
      accept(JSON.parse((e as MessageEvent<string>).data) as Snapshot);
    } catch {
      /* a broken frame: the next one replaces it */
    }
  });
  source.addEventListener("ping", () => {
    lastBeat = now();
    if (stream !== "live") stream = "live";
    if (ledgerError) ledgerError = null;
    paintBanner();
  });
  source.addEventListener("ledger-error", (e) => {
    try {
      ledgerError = (JSON.parse((e as MessageEvent<string>).data) as { error: string }).error;
    } catch {
      ledgerError = "unknown error";
    }
    paint();
  });
  source.onerror = () => {
    stream = "dropped";
    paintBanner();
    // A closed stream with no session means a 401: ask the server instead of retrying forever.
    if (source?.readyState === EventSource.CLOSED) void checkSession();
  };
}

async function checkSession(): Promise<void> {
  try {
    const s = await sessionInfo();
    if (!s.authenticated) await endSession("Your session ended. Sign in again.");
    else setTimeout(connect, 2000);
  } catch {
    setTimeout(checkSession, 3000);
  }
}

async function start(): Promise<void> {
  const s = await sessionInfo();
  info = { ...s, skew: s.now - Date.now() };
  if (!s.authenticated) return paintGate();
  skew = info.skew;
  appEl.classList.remove("is-gate");
  gateBusy = false;
  paintTopbar();
  paintRail();
  paint(true);
  await loadSnapshot();
  connect();
}

// ---------------------------------------------------------------- clock tick

let tick = 0;
setInterval(() => {
  tick += 1;
  if (!info?.authenticated || info.until === null) return;
  const left = info.until - now();
  const el = document.getElementById("timer-value");
  if (el) el.textContent = mmss(left);
  document.getElementById("timer")?.classList.toggle("is-low", left < 5 * 60_000);
  // The server slides the session on use; refresh our copy of its end every 5 minutes.
  if (tick % 300 === 0 || left <= 0) void sessionInfo().then((s) => {
    if (!s.authenticated) return endSession("Your session ended. Sign in again.");
    if (info) info.until = s.until;
  }).catch(() => {});
  if (tick % 5 === 0) {
    refreshTimes(document.body, now());
    paintBanner();
  }
}, 1000);

// ---------------------------------------------------------------- boot

window.addEventListener("hashchange", () => {
  route = parseHash(location.hash);
  confirmOff = false;
  paintRail();
  paint(true);
  if (route.view !== "office") main.focus({ preventScroll: true });
});
window.addEventListener("harness-theme", () => {
  paintTopbar();
  if (route.view === "office") onThemeChange(makeCtx());
});

paint(true);
start().catch((e: Error) => {
  loadError = e.message;
  appEl.classList.remove("is-gate");
  paint(true);
});
