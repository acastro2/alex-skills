import { h, timeEl } from "../dom.ts";
import type { Ctx, WorktreeRow } from "../ctx.ts";
import { chip, dataTable, detailRow, empty, sessionLink, td, viewHeader, type Tone } from "../parts.ts";

function syncChip(w: WorktreeRow) {
  const s = w.sync_state ?? "unknown";
  const tone: Tone = s === "conflict" ? "red" : s === "current" ? "green" : "neutral";
  return chip(tone, s);
}

export function renderWorktrees(ctx: Ctx): HTMLElement {
  const rows = [...ctx.snap.views.worktrees].sort((a, b) => Number(b.sync_state === "conflict") - Number(a.sync_state === "conflict"));
  const body: HTMLElement[] = [];
  for (const w of rows) {
    const selected = ctx.route.id === w.id;
    const conflict = w.sync_state === "conflict";
    body.push(
      h(
        "tr",
        { class: `${selected ? "selected" : ""}${conflict ? " has-detail" : ""}${w.state === "removed" ? " is-ended" : ""}`, "data-selected": selected ? "true" : undefined, "aria-current": selected ? "true" : undefined },
        td("Branch", "c-session", h("span", { class: "mono strong" }, w.branch ?? "no branch"), h("span", { class: "dim mono block path" }, w.path)),
        td("Repo", null, w.repo ?? h("span", { class: "dim" }, "unknown")),
        td("Owner", null, sessionLink(ctx, w.owner_slug, w.owner_session_id)),
        td("State", null, chip("neutral", w.state)),
        td("Sync", null, syncChip(w)),
        td("Synced", null, timeEl(w.synced_at, ctx.now)),
      ),
    );
    if (conflict) {
      body.push(
        detailRow(
          6,
          h("p", { class: "detail-lead" }, `${w.conflict_files.length} file${w.conflict_files.length === 1 ? "" : "s"} conflict with the base branch.`),
          h("ul", { class: "files mono" }, w.conflict_files.map((f) => h("li", null, f))),
          h("p", { class: "hint" }, w.owner_session_id ? "The owning session fixes it. Act only if the conflict stays." : "No session owns this worktree, so nobody is fixing the conflict."),
        ),
      );
    }
  }
  return h(
    "section",
    { class: "view" },
    viewHeader(ctx, "worktrees"),
    rows.length
      ? dataTable([{ label: "Branch" }, { label: "Repo" }, { label: "Owner" }, { label: "State" }, { label: "Sync" }, { label: "Synced" }], body, "Worktrees")
      : empty("No worktrees.", "A worktree shows here when a session or worker starts one. The harness reads them from git, never from the agent."),
  );
}
