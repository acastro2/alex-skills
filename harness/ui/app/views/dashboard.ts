// The dashboard: the home route. One screen of panels, all fed by the same snapshot the stream sends.
// The page is built once. Each snapshot patches the panels in place: a panel changes only when its data changed,
// the journal tail appends rows instead of re-rendering, and scroll position and focus survive an update.
import { h, icon, timeEl } from "../dom.ts";
import type { BundleRow, Ctx, JobRow, ProcessRow, SessionRow, TailKind, TailRow, ViewName, WorktreeRow } from "../ctx.ts";
import { hashFor } from "../ctx.ts";
import { btn, chip, grantUntil, lineChart, stateChip, type Tone } from "../parts.ts";
import { grantMergeButton } from "./changes.ts";
import { fmtGb, fmtMem, fmtPct, memPct, reasonsBox } from "./machine.ts";
import { onThemeChange, renderOffice, signals } from "./office.ts";

// ---------------------------------------------------------------- panel frame

interface Panel {
  el: HTMLElement;
  meta: HTMLElement;
  body: HTMLElement;
  scroll: number;
}

const sigs = new WeakMap<HTMLElement, string>();

/** Rebuild a host's children only when its data changed. Keeps scroll position and the focused item. */
function put(host: HTMLElement, sig: string, build: () => Node[]): void {
  if (sigs.get(host) === sig) return;
  sigs.set(host, sig);
  const top = host.scrollTop;
  const active = document.activeElement as HTMLElement | null;
  const key = active && host.contains(active) ? active.dataset.k ?? null : null;
  host.replaceChildren(...build());
  host.scrollTop = top;
  if (key) host.querySelector<HTMLElement>(`[data-k="${CSS.escape(key)}"]`)?.focus({ preventScroll: true });
}

function panel(cls: string, title: string, view: ViewName | null): Panel {
  const id = `ph-${cls}`;
  const meta = h("span", { class: "ph-meta" });
  const heading = view ? h("a", { class: "ph-link", href: hashFor(view), title: `Open ${title}` }, h("span", null, title), icon("chevron", 13)) : h("span", null, title);
  const body = h("div", { class: "pb" });
  const el = h("section", { class: `panel p-${cls}`, "aria-labelledby": id }, h("header", { class: "ph" }, h("h2", { class: "ph-title", id }, heading), meta), body);
  const p: Panel = { el, meta, body, scroll: 0 };
  body.addEventListener("scroll", () => {
    if (body.isConnected) p.scroll = body.scrollTop;
  }, { passive: true });
  return p;
}

const note = (text: string): HTMLElement => h("p", { class: "pb-empty dim" }, text);
const count = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const plain = (...kids: Array<string | null>): Node => document.createTextNode(kids.filter(Boolean).join(" · "));

// ---------------------------------------------------------------- the panels

const needs = panel("needs", "Needs you", "inbox");
const sessions = panel("sessions", "Live sessions", "sessions");
const tailP = panel("tail", "Journal tail", "journal");
const health = panel("health", "Harness health", "rules");
const procs = panel("proc", "Processes", "sessions");
const trees = panel("wt", "Worktrees", "worktrees");
const bundles = panel("bundles", "Proof bundles", "bundles");
const jobs = panel("jobs", "Jobs", "jobs");
const mach = panel("mach", "Machine", "machine");
const figSlot = h("section", { class: "panel p-fig", "aria-label": "Office figure" }, h("h2", { class: "sr" }, "Office figure"));

const col = (n: number, ...kids: HTMLElement[]) => h("div", { class: `dcol dcol-${n}` }, ...kids);
const root = h(
  "div",
  { class: "view dash" },
  h("h1", { class: "sr", id: "view-h" }, "Dashboard"),
  col(1, needs.el, health.el, jobs.el),
  col(2, sessions.el, procs.el),
  col(3, mach.el, tailP.el),
  col(4, figSlot, trees.el, bundles.el),
);

// ---------------------------------------------------------------- needs you

function paintNeeds(ctx: Ctx): void {
  const done = new Set(ctx.snap.views.changes.filter((c) => c.superseded || grantUntil(`apply:${c.id}`, c.granted) !== null).map((c) => c.id));
  const list = signals(ctx).filter((s) => !(s.view === "changes" && s.id && done.has(s.id)));
  const questions = new Map(ctx.snap.views.inbox.map((q) => [String(q.seq), q]));
  const ready = ctx.snap.pr_watches.filter((w) => w.state?.toUpperCase() === "OPEN" && w.review === "APPROVED" && !w.failed.length && w.pr !== null && w.session_id);
  const grantedUntil = (w: (typeof ready)[number]) => grantUntil(`merge:${w.pr}:${w.session_id}`, w.granted);
  const total = list.length + ready.filter((w) => grantedUntil(w) === null).length;
  put(needs.meta, String(total), () => [total ? chip("amber", String(total)) : h("span", { class: "dim" }, "none")]);
  put(needs.body, JSON.stringify([list, ready.map((w) => [w.id, w.pr, w.session_id, ctx.ui.pending.has(`merge:${w.pr}:${w.session_id}`), grantedUntil(w) === null ? null : Math.ceil(((grantedUntil(w) as number) - ctx.now) / 60_000)])]), () => {
    const mergeRows = ready.map((w) =>
      h(
        "div",
        { class: "need-merge" },
        h("span", { class: "need-head" }, chip("green", "ready to merge")),
        h("span", { class: "need-text" }, `${w.target} is approved and its checks pass.`),
        grantMergeButton(ctx, w.pr as number, w.session_id as string, w.granted, "Grant merge"),
      ),
    );
    if (!list.length) return mergeRows.length ? mergeRows : [note("Nothing needs you. A question, a stuck session, a conflict, a red bundle, a harness change or a failed job shows here.")];
    return [
      h(
        "ul",
        { class: "needs-list" },
        list.map((s) => {
          const q = s.view === "inbox" && s.id ? questions.get(s.id) : undefined;
          return h(
            "li",
            null,
            h(
              "a",
              { class: `need need-${s.tone}${q ? " need-q" : ""}`, href: hashFor(s.view, s.id), "data-k": `${s.view}:${s.id}` },
              h("span", { class: "need-head" }, chip(s.tone, s.what), s.at ? timeEl(s.at, ctx.now) : null, q ? h("span", { class: "dim" }, count(q.options.length, "option")) : null),
              h("span", { class: "need-text" }, s.detail),
            ),
          );
        }),
      ),
      ...mergeRows,
    ];
  });
}

// ---------------------------------------------------------------- live sessions

const RANK: Record<string, number> = { waiting: 0, stuck: 0, running: 1, idle: 2, ended: 3 };

function toolCall(s: SessionRow): HTMLElement | null {
  const t = s.last_tool;
  if (!t) return null;
  const now = t.event === "tool.before" && s.running;
  return h(
    "span",
    { class: "toolcall mono" },
    h("span", { class: `tc-when${now ? " is-now" : ""}` }, now ? "now" : "last"),
    h("span", { class: "tc-name" }, t.name),
    t.arg ? h("span", { class: "tc-arg dim" }, t.arg) : null,
    t.outcome === "deny" ? h("span", { class: "tc-deny" }, "denied") : null,
  );
}

function paintSessions(ctx: Ctx): void {
  const all = [...ctx.snap.views.sessions].sort((a, b) => (RANK[a.state] ?? 2) - (RANK[b.state] ?? 2) || (b.last_event_at ?? 0) - (a.last_event_at ?? 0));
  const live = all.filter((s) => s.state !== "ended");
  const slugs = new Map(all.map((s) => [s.id, s.slug]));
  const running = live.filter((s) => s.running).length;
  const stuck = live.filter((s) => s.stuck).length;
  put(sessions.meta, JSON.stringify([live.length, running, stuck, all.length - live.length]), () => [
    plain(`${live.length} live`, `${running} running`, all.length > live.length ? `${all.length - live.length} ended` : null),
    stuck ? chip("amber", `${stuck} stuck`) : null,
  ].filter((n): n is Node => n !== null));
  put(sessions.body, JSON.stringify(all.map((s) => [s.id, s.state, s.goal, s.turn, s.nudges, s.worktree, s.workers, s.last_tool, s.model, s.tool, s.running, s.parent_session_id])), () => {
    if (!all.length) return [note("No sessions on this host yet. A session shows here from its first prompt.")];
    return [
      h(
        "ul",
        { class: "sess-list" },
        all.map((s) =>
          h(
            "li",
            { class: `sess sess-${s.state}` },
            h(
              "a",
              { class: "sess-link", href: hashFor("sessions", s.id), "data-k": s.id },
              h("span", { class: "sess-id" }, stateChip(s), h("span", { class: "mono strong sess-slug" }, s.slug), h("span", { class: "mono dim sess-model" }, [s.tool, s.model].filter(Boolean).join(" · ")), s.last_event_at ? timeEl(s.last_event_at, ctx.now) : null),
              h("span", { class: "sess-what" }, h("span", { class: "sess-goal" }, s.goal ?? h("span", { class: "dim" }, "No goal yet")), toolCall(s)),
              h(
                "span",
                { class: "sess-meta mono dim" },
                `turn ${s.turn}`,
                s.nudges ? h("span", { class: s.nudges >= 3 ? "warn-text" : "" }, count(s.nudges, "nudge")) : null,
                s.worktree ? h("span", { class: "sess-wt" }, s.worktree) : null,
                s.workers ? h("span", null, count(s.workers, "worker")) : null,
                s.parent_session_id ? h("span", null, `worker of ${slugs.get(s.parent_session_id) ?? "a session"}`) : null,
              ),
            ),
          ),
        ),
      ),
    ];
  });
}

// ---------------------------------------------------------------- journal tail

type Filter = "all" | TailKind;
const FILTERS: Filter[] = ["all", "deny", "advise", "sendback"];
const tailUi = {
  list: h("ul", { class: "tail-list", "data-filter": "all", tabindex: "0", "aria-label": "Newest journal rows, oldest first" }),
  state: h("span", { class: "tail-state dim", role: "status" }),
  chips: new Map<Filter, HTMLButtonElement>(),
  filter: "all" as Filter,
  lastSeq: 0,
  top: 0,
  up: false,
  unseen: 0,
};
const TAIL_MAX = 160;

// The pointer is asked, not remembered: a missed mouseleave must never leave the tail paused for good.
const hovering = () => tailUi.list.matches(":hover");
const follow = () => !hovering() && !tailUi.up;
const toBottom = () => {
  tailUi.list.scrollTop = tailUi.list.scrollHeight;
};

function paintTailState(): void {
  const t = tailUi;
  const text = follow() ? "Following" : t.up ? "Paused: scrolled up" : "Paused while you hover";
  const full = t.unseen > 0 ? `${text} · ${t.unseen} new` : text;
  if (t.state.textContent !== full) t.state.textContent = full;
  jump.hidden = !(t.up || t.unseen > 0);
}

const jump = btn("Jump to latest", {
  tone: "quiet",
  onClick: () => {
    tailUi.up = false;
    tailUi.unseen = 0;
    toBottom();
    paintTailState();
  },
});
jump.hidden = true;

tailUi.list.addEventListener("mouseenter", paintTailState);
tailUi.list.addEventListener("mouseleave", () => {
  if (!tailUi.up) {
    tailUi.unseen = 0;
    toBottom();
  }
  paintTailState();
});
tailUi.list.addEventListener("scroll", () => {
  const l = tailUi.list;
  if (!l.isConnected || l.clientHeight === 0) return; // a detached list reports a scroll position of 0
  tailUi.top = l.scrollTop;
  tailUi.up = l.scrollHeight - l.scrollTop - l.clientHeight > 24;
  if (!tailUi.up) tailUi.unseen = 0;
  paintTailState();
}, { passive: true });

const chipRow = h(
  "div",
  { class: "tail-tools" },
  h("div", { class: "tail-chips", role: "group", "aria-label": "Show only" }, ...FILTERS.map((f) => {
    const b = h("button", { type: "button", class: "fchip", "aria-pressed": String(f === "all"), onClick: () => setFilter(f === tailUi.filter ? "all" : f) });
    tailUi.chips.set(f, b);
    return b;
  })),
  tailUi.state,
  jump,
);
tailP.body.append(tailUi.list);
tailP.el.insertBefore(chipRow, tailP.body);

function setFilter(f: Filter): void {
  tailUi.filter = f;
  tailUi.list.dataset.filter = f;
  for (const [k, b] of tailUi.chips) b.setAttribute("aria-pressed", String(k === f));
  if (follow()) toBottom();
}

function tailRow(r: TailRow, now: number, fresh: boolean): HTMLElement {
  const li = h(
    "li",
    { class: `tl${r.kind ? ` tl-${r.kind}` : ""}${fresh ? " is-new" : ""}`, "data-seq": r.seq, "data-kind": r.kind ?? "", title: `${r.event}${r.outcome ? ` · ${r.outcome}` : ""}${r.rule_id ? ` · ${r.rule_id}` : ""}\n${r.text}` },
    timeEl(r.time, now, "clock"),
    h("span", { class: "tl-tag mono" }, r.kind ?? r.event.split(".").pop()),
    h("span", { class: "tl-who mono" }, r.session_slug ?? "harness"),
    h("span", { class: "tl-text" }, r.tool ? h("span", { class: "tl-tool mono" }, r.tool) : null, r.text),
  );
  if (fresh) setTimeout(() => li.classList.remove("is-new"), 2600);
  return li;
}

function paintTail(ctx: Ctx): void {
  const hl = ctx.snap.dash.health;
  const label: Record<Filter, string> = { all: "All", deny: `Deny ${hl.deny_1h}`, advise: `Advise ${hl.advise_1h}`, sendback: `Send-back ${hl.sendback_1h}` };
  for (const [k, b] of tailUi.chips) if (b.textContent !== label[k]) b.textContent = label[k];

  const rows = [...ctx.snap.dash.tail].reverse(); // snapshot is newest first; a tail reads oldest first
  const first = tailUi.lastSeq === 0;
  const fresh = rows.filter((r) => r.seq > tailUi.lastSeq);
  if (fresh.length) {
    tailUi.list.append(...fresh.map((r) => tailRow(r, ctx.now, !first)));
    tailUi.lastSeq = fresh[fresh.length - 1].seq;
    while (tailUi.list.childElementCount > TAIL_MAX) tailUi.list.firstElementChild?.remove();
    if (follow()) toBottom();
    else if (!first) tailUi.unseen += fresh.length;
  }
  put(tailP.meta, String(ctx.snap.views.journal.per_min), () => [plain(`${ctx.snap.views.journal.per_min.toFixed(1)} rows a minute`)]);
  paintTailState();
}

// ---------------------------------------------------------------- harness health

const SVG = "http://www.w3.org/2000/svg";

function spark(series: number[]): SVGSVGElement {
  const max = Math.max(1, ...series);
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", `0 0 ${series.length * 4} 40`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("class", "spark");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `Journal rows a minute over the last hour. Peak ${max}. Now ${series[series.length - 1]}.`);
  series.forEach((n, i) => {
    const hgt = n === 0 ? 0.6 : Math.max(1.5, (n / max) * 38);
    const r = document.createElementNS(SVG, "rect");
    r.setAttribute("x", String(i * 4 + 0.5));
    r.setAttribute("y", String(40 - hgt));
    r.setAttribute("width", "3");
    r.setAttribute("height", String(hgt));
    if (i === series.length - 1) r.setAttribute("class", "is-partial");
    svg.append(r);
  });
  return svg;
}

function paintHealth(ctx: Ctx): void {
  const hl = ctx.snap.dash.health;
  const on = ctx.snap.harness.on;
  const peak = Math.max(0, ...hl.series);
  put(health.body, JSON.stringify([on, ctx.snap.harness.changed_at, hl, ctx.snap.views.journal.per_min]), () => {
    const chain = hl.chain_ok === null ? ["neutral", "Chain not checked"] : hl.chain_ok ? ["green", "Chain intact"] : ["red", `Chain broken at row ${hl.chain_bad_seq ?? "?"}`];
    const stat = (n: number, label: string, t: Tone) => h("div", { class: `stat stat-${n > 0 ? t : "zero"}` }, h("span", { class: "stat-n mono" }, String(n)), h("span", { class: "stat-l" }, label));
    return [
      h(
        "div",
        { class: "health" },
        h("div", { class: "health-state" }, h("span", { class: `state-dot ${on ? "is-on" : "is-off"}`, "aria-hidden": "true" }), h("span", { class: "strong" }, on ? "Harness on" : "Harness off"), ctx.snap.harness.changed_at ? h("span", { class: "dim" }, "since ", timeEl(ctx.snap.harness.changed_at, ctx.now)) : null),
        h("div", { class: "health-chain" }, chip(chain[0] as Tone, chain[1]), hl.chain_checked_at ? h("span", { class: "dim" }, "checked ", timeEl(hl.chain_checked_at, ctx.now)) : null),
        h("div", { class: "stats" }, stat(hl.deny_1h, "deny", "red"), stat(hl.advise_1h, "advise", "amber"), stat(hl.sendback_1h, "send-back", "amber"), h("span", { class: "stats-note dim" }, "in the last hour")),
        h("div", { class: "spark-box" }, spark(hl.series), h("div", { class: "spark-axis mono dim" }, h("span", null, "60 min ago"), h("span", null, `peak ${peak} a minute`), h("span", null, "now"))),
      ),
    ];
  });
}

// ---------------------------------------------------------------- machine

function sparkBox(title: string, now: number | null, values: (number | null)[], what: string): HTMLElement {
  const pk = Math.max(0, ...values.flatMap((v) => (v === null ? [] : [v])));
  return h(
    "div",
    { class: "mach-spark" },
    h("div", { class: "mach-spark-head" }, h("span", { class: "dim" }, title), h("span", { class: "mach-spark-n mono" }, fmtPct(now))),
    h("div", { class: "mach-spark-chart" }, lineChart(values, { label: `${what} over the last 60 minutes. Peak ${pk.toFixed(0)} percent. Now ${now === null ? "not known" : `${now.toFixed(0)} percent`}.` })),
  );
}

function paintMachine(ctx: Ctx): void {
  const r = ctx.snap.resources ?? null;
  put(mach.meta, JSON.stringify(r ? [r.tone, r.os] : null), () => [r ? (r.tone === "ok" ? plain("Within limits") : chip(r.tone, r.tone === "amber" ? "Needs a look" : "Over limit")) : h("span", { class: "dim" }, "no samples")]);
  put(mach.body, JSON.stringify(r), () => {
    if (!r) return [note("No samples yet. The machine numbers show here after the first sample.")];
    const worst = [...r.disks].sort((a, b) => b.used_pct - a.used_pct)[0] ?? null;
    const stat = (k: string, v: string, sub: string | null) => h("div", { class: "mach-stat" }, h("span", { class: "mach-stat-k dim" }, k), h("span", { class: "mach-stat-v mono" }, v), sub ? h("span", { class: "mach-stat-s mono dim", title: sub }, sub) : null);
    const top = r.top_cpu.slice(0, 5);
    return [
      h(
        "div",
        { class: "mach-dash" },
        reasonsBox(r),
        h("div", { class: "mach-sparks" }, sparkBox("CPU use", r.cpu.total, r.series.map((p) => p.cpu), "CPU use"), sparkBox("Memory use", memPct(r), r.series.map((p) => p.mem), "Memory use")),
        h(
          "div",
          { class: "mach-stats" },
          stat("Load 1 min", r.load ? r.load.one.toFixed(2) : "n/a", `${r.cpu.count} ${r.cpu.count === 1 ? "core" : "cores"}`),
          stat("Swap used", r.memory && r.memory.swap_total_mb > 0 ? fmtPct(r.memory.swap_pct) : "none", r.memory && r.memory.swap_total_mb > 0 ? fmtMem(r.memory.swap_used_mb) : null),
          stat("Fullest disk", worst ? fmtPct(worst.used_pct) : "n/a", worst ? `${worst.mount}, ${fmtGb(worst.free_gb)} free` : null),
          stat("Memory pressure", r.pressure ? fmtPct(r.pressure.memory, 1) : "n/a", r.pressure ? "10 s average" : null),
        ),
        top.length
          ? h(
              "table",
              { class: "dt" },
              h("caption", { class: "sr" }, "Five processes using the most CPU"),
              h("thead", null, h("tr", null, ["PID", "CPU %", "RSS MB", "Command"].map((t, i) => h("th", { scope: "col", class: i < 3 ? "num" : undefined }, t)))),
              h("tbody", null, top.map((p) => h("tr", null, h("td", { class: "num mono" }, String(p.pid)), h("td", { class: "num mono" }, p.cpu.toFixed(1)), h("td", { class: "num mono" }, String(Math.round(p.rss_mb))), h("td", { class: "mono cmd", title: p.args || p.comm }, p.args || p.comm)))),
            )
          : null,
      ),
    ];
  });
}

// ---------------------------------------------------------------- processes

function paintProcs(ctx: Ctx): void {
  const rows: ProcessRow[] = ctx.snap.dash.processes;
  const live = rows.filter((p) => p.ended_at === null);
  const kept = live.filter((p) => p.keep).length;
  put(procs.meta, JSON.stringify([live.length, kept]), () => [plain(`${live.length} live`, kept ? `${kept} kept` : null)]);
  put(procs.body, JSON.stringify(rows), () => {
    if (!rows.length) return [note("No processes reported. A server or watcher a session starts shows here with its port.")];
    return [
      h(
        "table",
        { class: "dt" },
        h("caption", { class: "sr" }, "Processes the sessions started"),
        h("thead", null, h("tr", null, ["PID", "Command", "Port", "Session", "Keep", "Started", "State"].map((t, i) => h("th", { scope: "col", class: [i === 0 || i === 2 ? "num" : "", i === 3 || i === 4 ? "hide-md" : ""].join(" ").trim() || undefined }, t)))),
        h(
          "tbody",
          null,
          rows.map((p) =>
            h(
              "tr",
              { class: p.ended_at !== null ? "is-ended" : undefined },
              h("td", { class: "num mono" }, p.pid === null ? "none" : String(p.pid)),
              h("td", { class: "mono cmd", title: p.command ?? "" }, p.command ?? ""),
              h("td", { class: "num mono" }, p.port === null ? "" : String(p.port)),
              h("td", { class: "hide-md" }, p.session_id ? h("a", { class: "mono link", href: hashFor("sessions", p.session_id) }, p.session_slug ?? p.session_id.slice(-6)) : h("span", { class: "dim" }, "none")),
              h("td", { class: "hide-md" }, p.keep ? chip("neutral", "keep") : null),
              h("td", null, p.started_at ? timeEl(p.started_at, ctx.now) : h("span", { class: "dim" }, "unknown")),
              h("td", null, p.ended_at === null ? chip("green", "live") : h("span", { class: "dim" }, "ended ", timeEl(p.ended_at, ctx.now))),
            ),
          ),
        ),
      ),
    ];
  });
}

// ---------------------------------------------------------------- worktrees

const SYNC: Record<string, [Tone, string]> = { conflict: ["red", "conflict"], behind: ["amber", "behind"], current: ["green", "current"] };
const SYNC_RANK: Record<string, number> = { conflict: 0, behind: 1, current: 2 };

function paintTrees(ctx: Ctx): void {
  const rows = [...ctx.snap.views.worktrees].sort((a, b) => (SYNC_RANK[a.sync_state ?? ""] ?? 3) - (SYNC_RANK[b.sync_state ?? ""] ?? 3) || (b.created_at ?? 0) - (a.created_at ?? 0));
  const conflict = rows.filter((w) => w.sync_state === "conflict").length;
  const behind = rows.filter((w) => w.sync_state === "behind").length;
  put(trees.meta, JSON.stringify([rows.length, conflict, behind]), () => [plain(count(rows.length, "worktree"), behind ? `${behind} behind` : null), conflict ? chip("red", `${conflict} conflict`) : null].filter((n): n is Node => n !== null));
  put(trees.body, JSON.stringify(rows), () => {
    if (!rows.length) return [note("No worktrees. A worker's branch shows here with its sync state.")];
    return [
      h(
        "ul",
        { class: "rows" },
        rows.map((w: WorktreeRow) => {
          const [t, text] = SYNC[w.sync_state ?? ""] ?? ["neutral", w.sync_state ?? "unknown"];
          return h(
            "li",
            null,
            h(
              "a",
              { class: "row", href: hashFor("worktrees", w.id), "data-k": w.id },
              h("span", { class: "row-head" }, chip(t, text), h("span", { class: "mono strong row-main" }, w.branch ?? w.path), h("span", { class: "dim row-side" }, w.state !== "active" ? w.state : null)),
              h("span", { class: "row-sub mono dim" }, w.owner_slug ?? "no owner", " · ", w.path),
              w.conflict_files.length ? h("span", { class: "row-conflict mono" }, w.conflict_files.join(", ")) : null,
            ),
          );
        }),
      ),
    ];
  });
}

// ---------------------------------------------------------------- proof bundles

function paintBundles(ctx: Ctx): void {
  const rows = [...ctx.snap.views.bundles].sort((a, b) => b.time - a.time).slice(0, 12);
  const green = rows.filter((b) => b.verdict === "green").length;
  const red = rows.filter((b) => b.verdict === "red").length;
  put(bundles.meta, JSON.stringify([rows.length, green, red]), () => [plain(`${green} green`), red ? chip("red", `${red} red`) : null].filter((n): n is Node => n !== null));
  put(bundles.body, JSON.stringify(rows.map((b) => [b.id, b.verdict, b.head_sha, b.summary, b.gate, b.session_slug, b.time])), () => {
    if (!rows.length) return [note("No proof bundles yet. A worker's bundle shows here with the harness's own re-run verdict.")];
    return [
      h(
        "ul",
        { class: "rows" },
        rows.map((b: BundleRow) =>
          h(
            "li",
            null,
            h(
              "a",
              { class: "row", href: hashFor("bundles", b.id), "data-k": b.id },
              h("span", { class: "row-head" }, chip(b.verdict === "green" ? "green" : b.verdict === "red" ? "red" : "neutral", b.verdict ?? "none"), h("span", { class: "mono strong row-main" }, b.head_sha ? b.head_sha.slice(0, 8) : "no sha"), h("span", { class: "dim row-side" }, b.session_slug, " ", timeEl(b.time, ctx.now))),
              h("span", { class: "row-sub" }, b.summary ?? "No summary"),
              b.gate ? h("span", { class: `row-gate mono ${b.gate.outcome === "red" || b.verdict === "red" ? "is-bad" : "dim"}` }, b.gate.reason ?? `push gate: ${b.gate.outcome ?? "unknown"}`) : null,
            ),
          ),
        ),
      ),
    ];
  });
}

// ---------------------------------------------------------------- jobs

function paintJobs(ctx: Ctx): void {
  const rows: JobRow[] = ctx.snap.views.jobs;
  const failed = rows.filter((j) => j.result === "failed").length;
  put(jobs.meta, JSON.stringify([rows.length, failed]), () => [plain(count(rows.length, "job")), failed ? chip("red", `${failed} failed`) : null].filter((n): n is Node => n !== null));
  put(jobs.body, JSON.stringify(rows), () => {
    if (!rows.length) return [note("No scheduled jobs.")];
    return [
      h(
        "table",
        { class: "dt" },
        h("caption", { class: "sr" }, "Scheduled jobs"),
        h("thead", null, h("tr", null, ["Job", "Last run", "Result", "Next run"].map((t) => h("th", { scope: "col" }, t)))),
        h(
          "tbody",
          null,
          rows.map((j) =>
            h(
              "tr",
              null,
              h("td", { class: "mono strong" }, h("a", { class: "link", href: hashFor("jobs", j.name) }, j.name), j.schedule ? h("span", { class: "sub" }, j.schedule) : null),
              h("td", null, timeEl(j.last_run_at, ctx.now)),
              h("td", { title: j.last_result ?? "" }, chip(j.result === "failed" ? "red" : j.result === "ok" ? "green" : "neutral", j.result)),
              h("td", null, j.next_run_at ? timeEl(j.next_run_at, ctx.now) : h("span", { class: "dim" }, "none")),
            ),
          ),
        ),
      ),
    ];
  });
}

// ---------------------------------------------------------------- the office figure

let figureRoot: HTMLElement | null = null;
let wasConnected = false;

/**
 * The figure carries its own frame and caption, so it goes in bare. office.ts builds the figure's mount root and
 * wraps it in its own page; take the root out of that wrapper once and keep it. The stream's snapshot hook
 * (main.ts) feeds the figure from then on.
 */
function mountFigure(ctx: Ctx): void {
  if (!figureRoot) {
    figureRoot = renderOffice(ctx).querySelector<HTMLElement>("#figure");
    if (figureRoot) figSlot.append(figureRoot);
  } else if (!wasConnected) onThemeChange(ctx);
}

// ---------------------------------------------------------------- entry

/** Patch the dashboard with the snapshot in `ctx` and return the one persistent root. */
export function renderDashboard(ctx: Ctx): HTMLElement {
  const returning = !root.isConnected;
  paintNeeds(ctx);
  paintSessions(ctx);
  paintTail(ctx);
  paintHealth(ctx);
  paintMachine(ctx);
  paintProcs(ctx);
  paintTrees(ctx);
  paintBundles(ctx);
  paintJobs(ctx);
  mountFigure(ctx);
  wasConnected = root.isConnected;
  // A detached element forgets its scroll position: put each panel back once main.ts attaches the root.
  if (returning) {
    requestAnimationFrame(() => {
      for (const p of [needs, sessions, procs, trees, bundles, jobs, health, mach]) p.body.scrollTop = p.scroll;
      if (follow()) toBottom();
      else tailUi.list.scrollTop = tailUi.top;
      wasConnected = root.isConnected;
    });
  }
  return root;
}
