import { h, firstLine, timeEl } from "../dom.ts";
import type { Ctx, SessionRow } from "../ctx.ts";
import { dataTable, empty, journalLink, modelId, stateChip, td, viewHeader } from "../parts.ts";

const RANK: Record<string, number> = { waiting: 0, stuck: 0, running: 1, idle: 2, ended: 3 };

/** Parents first by need, each followed by its workers. A worker whose parent is gone stands alone. */
function ordered(rows: SessionRow[]): { row: SessionRow; worker: boolean }[] {
  const ids = new Set(rows.map((r) => r.id));
  const kids = new Map<string, SessionRow[]>();
  const top: SessionRow[] = [];
  for (const r of rows) {
    if (r.parent_session_id && ids.has(r.parent_session_id)) kids.set(r.parent_session_id, [...(kids.get(r.parent_session_id) ?? []), r]);
    else top.push(r);
  }
  const cmp = (a: SessionRow, b: SessionRow) => RANK[a.state] - RANK[b.state] || a.started_at - b.started_at;
  const out: { row: SessionRow; worker: boolean }[] = [];
  const need = (r: SessionRow) => Math.min(RANK[r.state], ...(kids.get(r.id) ?? []).map((k) => RANK[k.state]));
  for (const r of top.sort((a, b) => need(a) - need(b) || cmp(a, b))) {
    out.push({ row: r, worker: false });
    for (const k of (kids.get(r.id) ?? []).sort(cmp)) out.push({ row: k, worker: true });
  }
  return out;
}

export function renderSessions(ctx: Ctx): HTMLElement {
  const rows = ctx.snap.views.sessions;
  const body = ordered(rows).map(({ row: s, worker }) => {
    const selected = ctx.route.id === s.id;
    const tr = h(
      "tr",
      { class: `${selected ? "selected" : ""}${s.state === "ended" ? " is-ended" : ""}`, "data-selected": selected ? "true" : undefined, "aria-current": selected ? "true" : undefined },
      td(
        "Session",
        "c-session",
        h("span", { class: worker ? "worker-mark" : "" }, worker ? h("span", { class: "sr" }, "Worker of the session above. ") : null, h("span", { class: "mono strong" }, s.slug)),
        s.workers ? h("span", { class: "dim" }, ` · ${s.workers} worker${s.workers === 1 ? "" : "s"}`) : null,
      ),
      td("State", null, stateChip(s)),
      td("Tool and model", null, h("span", { class: "stack" }, h("span", null, s.tool ?? "unknown"), s.model ? modelId(s.model) : h("span", { class: "dim mono block" }, "model not recorded"))),
      td("Goal", "c-goal", s.goal ? firstLine(s.goal, 140) : h("span", { class: "dim" }, "No goal recorded")),
      td("Turn", "num", String(s.turn)),
      td("Nudges", "num", s.nudges ? h("span", { class: s.nudges >= 5 ? "warn-text" : "" }, `${s.nudges} of 5`) : h("span", { class: "dim" }, "0")),
      td("Last event", null, timeEl(s.last_event_at, ctx.now)),
      td("", "c-act", journalLink(s.id)),
    );
    return tr;
  });
  return h(
    "section",
    { class: "view" },
    viewHeader(ctx, "sessions"),
    rows.length
      ? dataTable(
          [{ label: "Session" }, { label: "State" }, { label: "Tool and model" }, { label: "Goal" }, { label: "Turn", cls: "num" }, { label: "Nudges", cls: "num" }, { label: "Last event" }, { label: "Actions", cls: "c-act" }],
          body,
          "Sessions on this host",
        )
      : empty("No sessions on this host.", "A session shows here when OpenCode or Claude Code starts one and the harness hooks see it."),
  );
}
