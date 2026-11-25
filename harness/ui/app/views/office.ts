// The office: the figure (built by the office lane) beside a text list of every signal in it.
// Until /office/office.js exists, a plain floor plan with the same mountOffice(el, state, opts) shape stands in.
import { clear, h, icon, timeEl } from "../dom.ts";
import type { Ctx, ViewName } from "../ctx.ts";
import { hashFor } from "../ctx.ts";
import { chip, empty, type Tone } from "../parts.ts";

declare global {
  interface Window {
    harnessTheme?: { choice(): string; resolved(): "light" | "dark"; set(c: string): void };
  }
}

type LedgerSnapshot_ = import("../ctx.ts").Snapshot["ledger"];
type PageSnapshot = import("../ctx.ts").Snapshot;

/** What an office part reports on click. The figure names a view and an item; `kind` is accepted as a fallback. */
export interface OfficeTarget {
  view?: string;
  kind?: string;
  id?: string | null;
}

export interface MountOpts {
  theme: "light" | "dark";
  onSelect: (target: OfficeTarget | string) => void;
}
type Mounted = void | { update?(state: unknown): void; destroy?(): void; setTheme?(t: string): void };
type MountFn = (el: HTMLElement, state: unknown, opts: MountOpts) => Mounted;
type StateFn = (snap: PageSnapshot, prev?: unknown) => unknown;

const KIND_TO_VIEW: Record<string, ViewName> = {
  session: "sessions", desk: "sessions", worker: "sessions", flag: "sessions", rack: "sessions",
  question: "inbox", tray: "inbox", inbox: "inbox",
  worktree: "worktrees", drawer: "worktrees", cabinet: "worktrees",
  bundle: "bundles",
  rule: "rules", breaker: "rules", fuse: "rules", lever: "rules",
  journal: "journal", ticker: "journal", tape: "journal", gauge: "journal", grant: "journal", stamp: "journal", wake: "journal", capsule: "journal", tube: "journal",
  change: "changes",
  job: "jobs", clock: "jobs",
  bell: "inbox",
  jobs: "jobs",
  grants: "journal",
  rules: "rules",
  steering: "journal",
};

export function targetToHash(t: OfficeTarget | string): string {
  const o: OfficeTarget = typeof t === "string" ? { view: t } : t;
  const raw = o.view ?? (o.kind ? KIND_TO_VIEW[o.kind] : undefined);
  const view = raw && (raw === "office" || ["inbox", "sessions", "worktrees", "bundles", "rules", "journal", "changes", "jobs"].includes(raw)) ? (raw as ViewName) : "office";
  const q: Record<string, string> = {};
  // A click on the ticker or stamp opens the journal, filtered to what that part shows.
  if (view === "journal" && (o.kind === "stamp" || o.kind === "grant" || o.kind === "grants")) q.event = "grant";
  return hashFor(view, view === "office" ? null : o.id ?? null, q);
}

let figure: { mount: MountFn; state: StateFn } | "missing" | null = null;
let loading: Promise<void> | null = null;
const root = h("div", { class: "figure", id: "figure" });
let mounted: Mounted = undefined;
let mountedTheme = "";
let prevState: unknown;
let usingPlaceholder = false;
let loadError: string | null = null;

async function loadFigure(): Promise<void> {
  if (figure || loading) return loading ?? undefined;
  loading = (async () => {
    // Paths are held in variables so the client bundler leaves them alone: the server serves both at run time.
    const officeUrl = "/office/office.js";
    const modelUrl = "/office/model.js";
    try {
      const [o, m] = await Promise.all([import(/* @vite-ignore */ officeUrl), import(/* @vite-ignore */ modelUrl)]);
      const mount = (o as { mountOffice?: MountFn }).mountOffice;
      const state = (m as { officeStateFromServer?: StateFn }).officeStateFromServer;
      figure = typeof mount === "function" && typeof state === "function" ? { mount, state } : "missing";
    } catch (e) {
      figure = "missing";
      loadError = (e as Error).message;
    }
  })();
  return loading;
}

function placeholderMount(el: HTMLElement, state: unknown, opts: MountOpts): Mounted {
  const snap = state as LedgerSnapshot_;
  clear(el);
  const live = snap.sessions.filter((s) => s.state !== "ended");
  const desks = live.slice(0, 8);
  el.append(
    h(
      "div",
      { class: "floor" },
      desks.length
        ? desks.map((s) =>
            h(
              "button",
              { type: "button", class: `desk desk-${s.state}${s.parent_session_id ? " desk-worker" : ""}`, onClick: () => opts.onSelect({ view: "sessions", id: s.id }) },
              h("span", { class: "desk-name mono" }, s.slug),
              h("span", { class: "desk-state" }, s.state === "waiting" ? "question in tray" : s.state),
            ),
          )
        : h("p", { class: "dim floor-empty" }, "No sessions on this host"),
      live.length > 8 ? h("button", { type: "button", class: "rack", onClick: () => opts.onSelect({ view: "sessions" }) }, `+${live.length - 8} more`) : null,
    ),
  );
  return { update: (next) => placeholderMount(el, next, opts) };
}

interface Signal {
  tone: Tone;
  view: ViewName;
  id: string | null;
  what: string;
  detail: string;
  at: number | null;
}

export function signals(ctx: Ctx): Signal[] {
  const out: Signal[] = [];
  const v = ctx.snap.views;
  for (const q of v.inbox) out.push({ tone: "amber", view: "inbox", id: String(q.seq), what: "Question waiting", detail: `${q.session_slug}: ${q.text}`, at: q.asked_at });
  for (const s of v.sessions) if (s.stuck) out.push({ tone: "amber", view: "sessions", id: s.id, what: "Stuck", detail: `${s.slug} after ${s.nudges} nudges`, at: s.last_event_at });
  for (const w of v.worktrees) if (w.sync_state === "conflict") out.push({ tone: "red", view: "worktrees", id: w.id, what: "Conflict", detail: `${w.branch ?? w.path}: ${w.conflict_files.length} file${w.conflict_files.length === 1 ? "" : "s"}${w.owner_session_id ? "" : ", no owner"}`, at: w.synced_at });
  for (const b of v.bundles) if (b.verdict === "red") out.push({ tone: "red", view: "bundles", id: b.id, what: "Red proof bundle", detail: `${b.head_sha?.slice(0, 8) ?? "no sha"}: ${b.summary ?? "no summary"}`, at: b.time });
  for (const c of v.changes) if (c.status === "pending") out.push({ tone: "amber", view: "changes", id: c.id, what: "Harness change waiting", detail: `${c.sha.slice(0, 8)} asked by ${c.session_slug ?? "unknown"}`, at: c.created_at });
  for (const j of v.jobs) if (j.result === "failed") out.push({ tone: "red", view: "jobs", id: j.name, what: "Job failed", detail: `${j.name}: ${j.last_result ?? ""}`, at: j.last_run_at });
  return out;
}

function signalList(ctx: Ctx): HTMLElement {
  const list = signals(ctx);
  const live = ctx.snap.views.sessions.filter((s) => s.state !== "ended");
  const running = live.filter((s) => s.running).length;
  return h(
    "aside",
    { class: "signals", "aria-labelledby": "signals-h" },
    h("h2", { id: "signals-h" }, "Needs you"),
    list.length
      ? h(
          "ul",
          { class: "signal-list" },
          list.map((s) =>
            h(
              "li",
              null,
              h(
                "a",
                { class: `signal signal-${s.tone}`, href: hashFor(s.view, s.id) },
                h("span", { class: "signal-what" }, chip(s.tone, s.what), s.at ? timeEl(s.at, ctx.now) : null),
                h("span", { class: "signal-detail" }, s.detail),
                icon("chevron", 14),
              ),
            ),
          ),
        )
      : empty("Nothing needs you.", "A waiting question, a stuck session, a conflict, a red bundle or a failed job shows here, and as a part of the office."),
    h(
      "p",
      { class: "floor-line" },
      `${live.length} live session${live.length === 1 ? "" : "s"}, ${running} running a turn. ${ctx.snap.harness.on ? "Harness on." : "Harness off."} ${ctx.snap.views.journal.per_min.toFixed(1)} journal rows a minute.`,
    ),
  );
}

/** Mount or update the figure inside the persistent root. Safe to call on every snapshot. */
async function paintFigure(ctx: Ctx): Promise<void> {
  await loadFigure();
  const theme = window.harnessTheme?.resolved() ?? "light";
  // The in-tray names a session; the inbox view names a question.
  const pick = (t: OfficeTarget | string): OfficeTarget | string => {
    if (typeof t === "string" || t.kind !== "inbox" || !t.id) return t;
    const q = ctx.snap.views.inbox.find((x) => x.session_id === t.id);
    return q ? { view: "inbox", id: String(q.seq) } : { view: "inbox" };
  };
  const opts: MountOpts = { theme, onSelect: (t) => ctx.go(targetToHash(pick(t))) };
  try {
    if (figure && figure !== "missing") {
      const state = figure.state(ctx.snap, prevState);
      prevState = state;
      if (mounted && mountedTheme === theme && typeof mounted.update === "function") mounted.update(state);
      else {
        mounted?.destroy?.();
        clear(root);
        mounted = figure.mount(root, state, opts);
        mountedTheme = theme;
      }
      usingPlaceholder = false;
    } else {
      usingPlaceholder = true;
      if (mounted && "update" in (mounted ?? {}) && mountedTheme === theme) (mounted as { update(s: unknown): void }).update(ctx.snap.ledger);
      else {
        clear(root);
        mounted = placeholderMount(root, ctx.snap.ledger, opts);
        mountedTheme = theme;
      }
    }
  } catch (e) {
    loadError = (e as Error).message;
    clear(root);
    root.append(h("p", { class: "inline-error", role: "alert" }, `The office figure failed: ${loadError}`));
    mounted = undefined;
  }
  const note = document.getElementById("figure-note");
  if (note) note.textContent = usingPlaceholder ? "Office figure not built yet. A plain floor plan stands in." : "";
}

export function renderOffice(ctx: Ctx): HTMLElement {
  void paintFigure(ctx);
  return h(
    "section",
    { class: "view view-office" },
    h("header", { class: "view-head" }, h("div", { class: "view-title" }, h("h1", { id: "view-h" }, "Office")), h("p", { class: "view-blurb" }, "One glance: is anything wrong on this host? Click a part to open the view behind it.")),
    h(
      "div",
      { class: "office-layout" },
      h(
        "section",
        { class: "plate office-plate", "aria-label": "Office figure" },
        h("span", { class: "cap cap-tl mono" }, "OFFICE"),
        h("span", { class: "cap cap-tr mono" }, `${ctx.snap.host}`),
        root,
        h("p", { class: "cap cap-bl mono", id: "figure-note" }, ""),
        h("span", { class: "cap cap-br mono" }, `seq ${ctx.snap.seq}`),
      ),
      signalList(ctx),
    ),
  );
}

export function onThemeChange(ctx: Ctx | null): void {
  if (ctx) void paintFigure(ctx);
}
