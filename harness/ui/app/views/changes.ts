import { h, sha, timeEl } from "../dom.ts";
import type { ChangeRow, Ctx } from "../ctx.ts";
import { btn, chip, dataTable, detailRow, empty, expandToggle, td, viewHeader, type Tone } from "../parts.ts";

const STATUS: Record<ChangeRow["status"], [Tone, string]> = {
  pending: ["amber", "waiting for your tap"],
  applied: ["green", "applied"],
  rolled_back: ["neutral", "rolled back"],
  other: ["neutral", "closed"],
};

export function renderChanges(ctx: Ctx): HTMLElement {
  const rows = ctx.snap.views.changes;
  const body: HTMLElement[] = [];
  for (const c of rows) {
    const key = `change:${c.id}`;
    const selected = ctx.route.id === c.id;
    const open = ctx.ui.expanded.has(key) || selected || c.status === "pending";
    const [tone, text] = STATUS[c.status];
    const applyKey = `apply:${c.id}`;
    const rollKey = `rollback:${c.id}`;
    body.push(
      h(
        "tr",
        { class: `${selected ? "selected" : ""}${open ? " is-open" : ""}`, "data-selected": selected ? "true" : undefined, "aria-current": selected ? "true" : undefined },
        td("Change", "c-session", expandToggle(ctx, key, sha(c.sha), open, h("span", { class: "mono strong" }, `${sha(c.sha)} · ${sha(c.digest)}`))),
        td("Status", null, chip(tone, text)),
        td("Asked by", null, c.session_slug ? h("span", { class: "mono" }, c.session_slug) : h("span", { class: "dim" }, "unknown")),
        td("Asked", null, timeEl(c.created_at, ctx.now)),
        td("Applied", null, c.apply?.applied_at ? timeEl(c.apply.applied_at, ctx.now) : h("span", { class: "dim" }, "not applied")),
        td(
          "",
          "c-act",
          c.status === "pending"
            ? btn("Approve with passkey", { tone: "primary", icon: "key", busy: ctx.ui.pending.has(applyKey), onClick: () => void ctx.act(applyKey, "apply", { request_id: c.id }, "Approved for 30 minutes. The change applies when the session runs `harness apply`.") })
            : c.status === "applied"
              ? btn("Roll back with passkey", { icon: "key", busy: ctx.ui.pending.has(rollKey), onClick: () => void ctx.act(rollKey, "rollback", { request_id: c.id }, "Rollback requested.") })
              : null,
        ),
      ),
    );
    if (open) {
      body.push(
        detailRow(
          6,
          h("h3", null, "Review the harness rendered"),
          c.review ? h("pre", { class: "review mono" }, c.review) : h("p", { class: "dim" }, "No review text was journaled for this change."),
          c.apply ? h("p", { class: "hint mono" }, `tree ${sha(c.apply.tree_hash, 12)}${c.apply.rolled_back_at ? " · rolled back" : ""}`) : null,
        ),
      );
    }
  }
  return h(
    "section",
    { class: "view" },
    viewHeader(ctx, "changes"),
    rows.length
      ? dataTable([{ label: "Change" }, { label: "Status" }, { label: "Asked by" }, { label: "Asked" }, { label: "Applied" }, { label: "Actions", cls: "c-act" }], body, "Harness changes")
      : empty("No harness changes.", "A change shows here when a session asks to change the harness itself. It waits for your passkey tap."),
  );
}
