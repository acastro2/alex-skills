// Journal and replay. The journal holds hundreds of thousands of rows, so the page asks the server for one
// page at a time (/api/journal) and never holds more than the pages Alex opened.
import { getJSON } from "../api.ts";
import { clear, firstLine, h, icon, timeEl } from "../dom.ts";
import type { Ctx, JournalPage, JournalRow } from "../ctx.ts";
import { hashFor } from "../ctx.ts";
import { btn, dataTable, empty, skeleton, td, viewHeader } from "../parts.ts";

const PAGE = 50;
const REPLAY_PAGE = 200;
const COMMON_EVENTS = ["prompt", "stop", "stop.sendback", "nudge", "session.stuck", "question.asked", "question.answered", "grant", "harness.wrong", "egress.warning", "watch.wake", "tool.before", "tool.after", "bundle"];
const SINCE: [string, string, number][] = [["1h", "Last hour", 3_600_000], ["24h", "Last 24 hours", 86_400_000], ["all", "All time", 0]];

// The view is rebuilt on some snapshots while a fetch is in flight. Fetches paint whatever view is current.
let active: { paint: () => void; bar: (seq: number) => void } | null = null;
let lastSeq = 0;

export function emptyJournal() {
  return {
    filters: { session: "", rule: "", event: "", q: "", since: "24h" },
    rows: [] as JournalRow[],
    hasMore: false,
    next: null as number | null,
    loading: false,
    error: null as string | null,
    topSeq: 0,
    key: "",
    routeSig: "",
    replay: null,
  };
}

function query(f: Ctx["ui"]["journal"]["filters"], extra: Record<string, string | number>): string {
  const p = new URLSearchParams();
  if (f.session) p.set("session", f.session);
  if (f.rule) p.set("rule", f.rule);
  if (f.event) p.set("event", f.event);
  if (f.q) p.set("q", f.q);
  const since = SINCE.find((s) => s[0] === f.since)?.[2] ?? 0;
  if (since) p.set("since", String(Date.now() - since));
  for (const [k, v] of Object.entries(extra)) p.set(k, String(v));
  return p.toString();
}

export function renderJournal(ctx: Ctx): HTMLElement {
  const j = ctx.ui.journal;
  const sig = JSON.stringify(ctx.route.q);
  if (j.routeSig !== sig) {
    j.routeSig = sig;
    const q = ctx.route.q;
    if (q.session !== undefined || q.rule !== undefined || q.event !== undefined) {
      j.filters = { session: q.session ?? "", rule: q.rule ?? "", event: q.event ?? "", q: q.q ?? "", since: q.since ?? "all" };
    }
    j.key = "";
    j.replay = null;
  }

  const results = h("div", { class: "journal-results" });
  const newBar = h("div", { class: "new-rows", hidden: true });
  const tools = h("form", { class: "filters", role: "search", "aria-label": "Journal filters", onSubmit: (e: Event) => e.preventDefault() });

  const fetchPage = async (mode: "reset" | "more") => {
    j.loading = true;
    j.error = null;
    active?.paint();
    try {
      const extra: Record<string, string | number> = { limit: PAGE };
      if (mode === "more" && j.next !== null) extra.before = j.next;
      const page = await getJSON<JournalPage>(`/api/journal?${query(j.filters, extra)}`);
      j.rows = mode === "more" ? [...j.rows, ...page.rows] : page.rows;
      j.hasMore = page.has_more;
      j.next = page.next_cursor;
      if (mode === "reset") j.topSeq = page.rows[0]?.seq ?? ctx.snap.seq;
      j.key = JSON.stringify(j.filters);
    } catch (e) {
      j.error = (e as Error).message;
    }
    j.loading = false;
    active?.paint();
    active?.bar(lastSeq);
  };

  const loadReplay = async (more: boolean) => {
    const r = j.replay;
    if (!r) return;
    r.loading = true;
    r.error = null;
    active?.paint();
    try {
      const after = more ? r.rows[r.rows.length - 1]?.seq ?? 0 : 0;
      const page = await getJSON<JournalPage>(`/api/journal?session=${encodeURIComponent(r.session)}&after=${after}&limit=${REPLAY_PAGE}`);
      r.rows = more ? [...r.rows, ...page.rows] : page.rows;
      r.hasMore = page.has_more;
    } catch (e) {
      r.error = (e as Error).message;
    }
    r.loading = false;
    active?.paint();
  };

  const newBarUpdate = (seq: number) => {
    const n = Math.max(0, seq - j.topSeq);
    newBar.hidden = n === 0 || j.replay !== null;
    clear(newBar);
    if (n > 0) newBar.append(h("span", null, `${n} newer row${n === 1 ? "" : "s"} in the journal. `), btn("Show newest", { tone: "quiet", onClick: () => void fetchPage("reset") }));
  };
  ctx.ui.pulse = (snap) => {
    lastSeq = snap.seq;
    newBarUpdate(snap.seq);
  };

  const slugOf = (id: string) => ctx.snap.views.sessions.find((s) => s.id === id)?.slug ?? id.slice(-8);
  const sessionOptions = [...ctx.snap.views.sessions];

  const select = (label: string, id: string, value: string, opts: [string, string][], onChange: (v: string) => void) =>
    h(
      "label",
      { class: "filter", for: id },
      h("span", null, label),
      (() => {
        const s = h("select", { id, class: "field", onChange: (e: Event) => onChange((e.target as HTMLSelectElement).value) }, opts.map(([v, t]) => h("option", { value: v, selected: v === value }, t)));
        s.value = value;
        return s;
      })(),
    );

  const replayBtn = btn("Replay session", {
    icon: "journal",
    disabled: !j.filters.session,
    title: j.filters.session ? "Step through this session, oldest row first" : "Pick a session first",
    onClick: () => {
      j.replay = { session: j.filters.session, rows: [], index: 0, hasMore: false, loading: true, error: null };
      void loadReplay(false);
    },
  });
  let timer: ReturnType<typeof setTimeout> | null = null;
  const apply = () => {
    replayBtn.disabled = !j.filters.session;
    replayBtn.title = j.filters.session ? "Step through this session, oldest row first" : "Pick a session first";
    j.replay = null;
    void fetchPage("reset");
  };
  const text = (label: string, id: string, value: string, list: string | null, set: (v: string) => void, ph: string) => {
    const input = h("input", { id, class: "field", type: "search", placeholder: ph, list, autocomplete: "off", onInput: (e: Event) => {
      set((e.target as HTMLInputElement).value);
      if (timer) clearTimeout(timer);
      timer = setTimeout(apply, 300);
    } });
    input.value = value;
    return h("label", { class: "filter", for: id }, h("span", null, label), input);
  };

  tools.append(
    select("Session", "f-session", j.filters.session, [["", "All sessions"], ...sessionOptions.map((s) => [s.id, s.slug] as [string, string]), ...(j.filters.session && !sessionOptions.some((s) => s.id === j.filters.session) ? [[j.filters.session, slugOf(j.filters.session)] as [string, string]] : [])], (v) => {
      j.filters.session = v;
      apply();
    }),
    select("Rule", "f-rule", j.filters.rule, [["", "All rules"], ...ctx.snap.views.rules.map((r) => [r.id, r.id] as [string, string])], (v) => {
      j.filters.rule = v;
      apply();
    }),
    text("Event", "f-event", j.filters.event, "events", (v) => (j.filters.event = v), "any, or stop.*"),
    text("Text", "f-q", j.filters.q, null, (v) => (j.filters.q = v), "reason or prompt"),
    select("Time", "f-since", j.filters.since, SINCE.map(([v, t]) => [v, t] as [string, string]), (v) => {
      j.filters.since = v;
      apply();
    }),
    h("datalist", { id: "events" }, COMMON_EVENTS.map((e) => h("option", { value: e }))),
    h(
      "div",
      { class: "filter-actions" },
      replayBtn,
      btn("Clear", {
        tone: "quiet",
        onClick: () => {
          j.filters = { session: "", rule: "", event: "", q: "", since: "24h" };
          ctx.go(hashFor("journal"));
          ctx.rerender();
        },
      }),
    ),
  );

  function rowEls(rows: JournalRow[], opts: { replay?: boolean; current?: number }): HTMLElement[] {
    const out: HTMLElement[] = [];
    rows.forEach((r, i) => {
      const key = `j:${r.seq}`;
      const open = opts.replay ? i === opts.current : ctx.ui.expanded.has(key);
      const future = opts.replay && opts.current !== undefined && i > opts.current;
      out.push(
        h(
          "tr",
          { class: `${open ? "is-open" : ""}${future ? " is-future" : ""}`, "aria-current": opts.replay && i === opts.current ? "step" : undefined, "data-selected": opts.replay && i === opts.current ? "true" : undefined },
          td(
            "Seq",
            "c-seq",
            opts.replay
              ? h("button", { type: "button", class: "twisty", "aria-label": `Go to step ${i + 1}`, onClick: () => step(i) }, h("span", { class: "mono" }, String(r.seq)))
              : h("button", { type: "button", class: "twisty", "aria-expanded": String(open), "aria-label": `Details: row ${r.seq}`, onClick: () => {
                  if (open) ctx.ui.expanded.delete(key);
                  else ctx.ui.expanded.add(key);
                  paint();
                } }, icon("chevron", 14), h("span", { class: "mono" }, String(r.seq))),
          ),
          td("Time", null, timeEl(r.time, ctx.now, "clock")),
          td("Session", null, r.session_id ? h("a", { class: "mono link", href: hashFor("sessions", r.session_id) }, r.session_slug ?? r.session_id.slice(-6)) : h("span", { class: "dim" }, "none")),
          td("Event", null, h("span", { class: "mono" }, r.event)),
          td("Rule", null, r.rule_id ? h("a", { class: "mono link", href: hashFor("rules", r.rule_id) }, r.rule_id) : h("span", { class: "dim" }, "none")),
          td("Outcome", null, r.outcome ? h("span", { class: `outcome outcome-${r.outcome}` }, r.outcome) : h("span", { class: "dim" }, "none")),
          td("Detail", "c-goal", firstLine(r.reason ?? r.prompt_text ?? toolOf(r.data) ?? "", 150) || h("span", { class: "dim" }, "no text")),
        ),
      );
      if (open) {
        out.push(
          h(
            "tr",
            { class: "detail" },
            h(
              "td",
              { colspan: "7" },
              h(
                "div",
                { class: "detail-box" },
                r.prompt_text ? h("pre", { class: "review mono" }, r.prompt_text) : null,
                r.reason && r.reason !== r.prompt_text ? h("p", null, r.reason) : null,
                r.data !== null && r.data !== undefined ? h("pre", { class: "review mono" }, JSON.stringify(r.data, null, 2)) : null,
                h("p", { class: "hint mono" }, `turn ${r.turn ?? "none"} · seq ${r.seq} · ${new Date(r.time).toLocaleString()}`),
              ),
            ),
          ),
        );
      }
    });
    return out;
  }

  const toolOf = (d: unknown): string | null => (d && typeof d === "object" && typeof (d as { tool?: unknown }).tool === "string" ? `tool: ${(d as { tool: string }).tool}` : null);
  const COLS = [{ label: "Seq" }, { label: "Time" }, { label: "Session" }, { label: "Event" }, { label: "Rule" }, { label: "Outcome" }, { label: "Detail" }];

  function step(i: number) {
    const r = j.replay;
    if (!r) return;
    r.index = Math.max(0, Math.min(i, r.rows.length - 1));
    paint();
    results.querySelector("[aria-current=step]")?.scrollIntoView({ block: "nearest" });
  }

  function paint() {
    clear(results);
    const r = j.replay;
    if (r) {
      const slug = slugOf(r.session);
      results.append(
        h(
          "div",
          { class: "replay-bar", role: "group", "aria-label": "Replay controls" },
          h("p", { class: "replay-title" }, h("strong", null, `Replaying ${slug}`), h("span", { class: "dim" }, r.rows.length ? ` · step ${r.index + 1} of ${r.rows.length}${r.hasMore ? "+" : ""}` : "")),
          h(
            "div",
            { class: "replay-actions" },
            btn("Back", { disabled: r.index === 0, onClick: () => step(r.index - 1) }),
            btn("Next", { tone: "primary", disabled: r.index >= r.rows.length - 1, onClick: () => step(r.index + 1) }),
            r.hasMore ? btn("Load more", { busy: r.loading, onClick: () => void loadReplay(true) }) : null,
            btn("Exit replay", { tone: "quiet", onClick: () => {
              j.replay = null;
              paint();
            } }),
          ),
          h("span", { class: "hint" }, "Arrow keys step. Rows after the current step are dimmed."),
        ),
      );
      if (r.error) results.append(h("p", { class: "inline-error", role: "alert" }, r.error));
      if (r.loading && !r.rows.length) results.append(skeleton(6));
      else if (!r.rows.length) results.append(empty("No rows for this session.", "The journal has nothing recorded for it yet."));
      else results.append(dataTable(COLS, rowEls(r.rows, { replay: true, current: r.index }), `Replay of ${slug}`));
      return;
    }
    if (j.error) results.append(h("p", { class: "inline-error", role: "alert" }, `The journal cannot be read: ${j.error}`));
    if (j.loading && !j.rows.length) results.append(skeleton(8));
    else if (!j.rows.length && !j.error) results.append(empty("No journal rows match.", "Rows show here as hooks record prompts, tool calls, send-backs and grants. Widen the time range or clear a filter."));
    else if (j.rows.length) {
      results.append(
        h("div", { class: j.loading ? "is-loading" : "" }, dataTable(COLS, rowEls(j.rows, {}), "Journal rows, newest first")),
        h(
          "div",
          { class: "pager" },
          h("span", { class: "dim" }, `${j.rows.length} row${j.rows.length === 1 ? "" : "s"} shown`),
          j.hasMore ? btn("Older rows", { busy: j.loading, onClick: () => void fetchPage("more") }) : h("span", { class: "dim" }, "That is the oldest row for these filters."),
        ),
      );
    }
  }

  results.addEventListener("keydown", (e) => {
    const r = j.replay;
    if (!r || (e.target as HTMLElement).closest("input,select,textarea")) return;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      step(r.index + 1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      step(r.index - 1);
    }
  });

  active = { paint, bar: newBarUpdate };
  lastSeq = ctx.snap.seq;
  paint();
  if (j.key !== JSON.stringify(j.filters) && !j.loading) void fetchPage("reset");
  else newBarUpdate(ctx.snap.seq);

  return h("section", { class: "view" }, viewHeader(ctx, "journal", h("span", { class: "rate mono" }, `${ctx.snap.views.journal.per_min.toFixed(1)} rows a minute`)), tools, newBar, results);
}
