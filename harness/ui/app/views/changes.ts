import { h, sha, timeEl } from "../dom.ts";
import type { ChangeRow, Ctx, PrWatchRow } from "../ctx.ts";
import { appliedChip, btn, chip, dataTable, detailRow, empty, expandToggle, grantChip, grantUntil, rememberGrant, td, viewHeader, type Tone } from "../parts.ts";

const STATUS: Record<ChangeRow["status"], [Tone, string]> = {
  pending: ["amber", "waiting for your tap"],
  applied: ["green", "applied"],
  rolled_back: ["neutral", "rolled back"],
  other: ["neutral", "closed"],
};

/** The one merge grant button. The page asks for a passkey tap; the server mints `MERGE-OK <pr>` for that session. */
export function grantMergeButton(ctx: Ctx, pr: number, sessionId: string, granted: { until: number } | null, label = "Grant merge with passkey"): HTMLElement {
  const key = `merge:${pr}:${sessionId}`;
  const until = grantUntil(key, granted);
  if (until !== null) return grantChip("merge", until, ctx.now);
  return btn(label, {
    tone: "primary",
    icon: "key",
    busy: ctx.ui.pending.has(key),
    onClick: () => void tap(ctx, key, "merge", { pr, session_id: sessionId }, "Merge granted for 30 minutes. The session lands it with `merge_pr`."),
  });
}

/** Run a passkey action; on success show the grant chip at once. The next snapshot confirms it. */
async function tap(ctx: Ctx, key: string, action: string, args: Record<string, unknown>, done: string, chipKey = key): Promise<void> {
  if (await ctx.act(key, action, args, done)) {
    rememberGrant(chipKey);
    ctx.rerender();
  }
}

const PR_CAP = 8;
const PR_ALL_KEY = "merge:all";

/** Approved first, then green checks, then the rest. Array.sort is stable, so the snapshot's newest-first order holds inside a rank. */
const prRank = (w: PrWatchRow) => (w.review === "APPROVED" ? 0 : 2) + (w.failed.length ? 1 : 0);

function watchedPrs(ctx: Ctx): HTMLElement | null {
  const all = [...ctx.snap.pr_watches].sort((a, b) => prRank(a) - prRank(b));
  if (!all.length) return null;
  const showAll = ctx.ui.expanded.has(PR_ALL_KEY);
  const rows = showAll ? all : all.slice(0, PR_CAP);
  const items = rows.map((w) =>
    h(
      "li",
      { class: "pr-row" },
      h("span", { class: "mono strong pr-target" }, w.target),
      w.review === "APPROVED" ? chip("green", "approved") : h("span", { class: "dim pr-state" }, [w.state?.toLowerCase(), w.review?.replace(/_/g, " ").toLowerCase()].filter(Boolean).join(" · ") || "unknown"),
      w.failed.length ? chip("red", `${w.failed.length} failed`) : null,
      h("span", { class: "mono dim pr-by" }, w.session_slug ?? "no session"),
      w.pr !== null && w.session_id ? grantMergeButton(ctx, w.pr, w.session_id, w.granted) : h("span", { class: "dim" }, "no PR number"),
    ),
  );
  return h(
    "div",
    { class: "pr-watched" },
    h("h3", { class: "merge-sub" }, `Watched (${all.length})`),
    h("ul", { class: "pr-list", "aria-label": "Watched pull requests" }, items),
    all.length > PR_CAP
      ? btn(showAll ? "Show fewer" : `Show all ${all.length}`, { tone: "quiet", ariaExpanded: showAll, onClick: () => ctx.toggle(PR_ALL_KEY) })
      : null,
  );
}

function mergeForm(ctx: Ctx): HTMLElement {
  const prKey = "merge:pr";
  const sesKey = "merge:session";
  const roots = ctx.snap.views.sessions.filter((s) => !s.parent_session_id && s.state !== "ended");
  const pr = ctx.ui.drafts.get(prKey) ?? "";
  const chosen = ctx.ui.drafts.get(sesKey) ?? roots[0]?.id ?? "";
  const key = "merge:grant";
  const prNum = Number(pr);
  const ready = Number.isInteger(prNum) && prNum > 0 && chosen !== "";
  return h(
    "section",
    { class: "merge-box", "aria-labelledby": "merge-h" },
    h("h2", { id: "merge-h" }, "Pull requests"),
    h("p", { class: "hint" }, "Give one session the right to merge one pull request. The grant lasts 30 minutes. It covers only this PR and this session."),
    watchedPrs(ctx),
    h("h3", { class: "merge-sub" }, "Another pull request"),
    h(
      "form",
      {
        class: "merge-form",
        onSubmit: (e: Event) => {
          e.preventDefault();
          if (!ready) return;
          void tap(ctx, key, "merge", { pr: prNum, session_id: chosen }, "Merge granted for 30 minutes. The session lands it with `merge_pr`.", `merge:${prNum}:${chosen}`);
        },
      },
      h(
        "label",
        { class: "merge-f" },
        h("span", null, "PR number"),
        h("input", { class: "field mono", type: "text", inputmode: "numeric", autocomplete: "off", name: "pr", value: pr, placeholder: "13", onInput: (e: Event) => ctx.ui.drafts.set(prKey, (e.target as HTMLInputElement).value.trim()) }),
      ),
      h(
        "label",
        { class: "merge-f" },
        h("span", null, "Session that merges"),
        h(
          "select",
          { class: "field mono", name: "session", disabled: roots.length === 0, onChange: (e: Event) => ctx.ui.drafts.set(sesKey, (e.target as HTMLSelectElement).value) },
          roots.length
            ? roots.map((s) => h("option", { value: s.id, selected: s.id === chosen }, `${s.slug} · ${s.state}`))
            : h("option", { value: "" }, "No live session"),
        ),
      ),
      btn("Grant merge with passkey", { tone: "primary", icon: "key", type: "submit", busy: ctx.ui.pending.has(key), disabled: roots.length === 0 }),
    ),
  );
}

const SUPERSEDED_KEY = "changes:superseded";

function changeRows(ctx: Ctx, rows: ChangeRow[]): HTMLElement[] {
  const body: HTMLElement[] = [];
  for (const c of rows) {
    const key = `change:${c.id}`;
    const applyKey = `apply:${c.id}`;
    const rollKey = `rollback:${c.id}`;
    const selected = ctx.route.id === c.id;
    const until = c.status === "pending" ? grantUntil(applyKey, c.granted) : null;
    const open = ctx.ui.expanded.has(key) || selected || (c.status === "pending" && until === null && !c.superseded);
    const [tone, text] = until !== null ? (["green", "approved"] as [Tone, string]) : STATUS[c.status];
    body.push(
      h(
        "tr",
        { class: `${selected ? "selected" : ""}${open ? " is-open" : ""}`, "data-selected": selected ? "true" : undefined, "aria-current": selected ? "true" : undefined },
        td("Change", "c-session", expandToggle(ctx, key, sha(c.sha), open, h("span", { class: "mono strong" }, `${sha(c.sha)} · ${sha(c.digest)}`))),
        td("Status", null, c.status === "applied" ? appliedChip(sha(c.sha)) : chip(tone, text)),
        td("Asked by", null, c.session_slug ? h("span", { class: "mono" }, c.session_slug) : h("span", { class: "dim" }, "unknown")),
        td("Asked", null, timeEl(c.created_at, ctx.now)),
        td("Applied", null, c.apply?.applied_at ? timeEl(c.apply.applied_at, ctx.now) : h("span", { class: "dim" }, "not applied")),
        td(
          "",
          "c-act",
          c.status === "pending"
            ? until !== null
              ? grantChip("harness", until, ctx.now)
              : btn("Approve with passkey", { tone: "primary", icon: "key", busy: ctx.ui.pending.has(applyKey), onClick: () => void tap(ctx, applyKey, "apply", { request_id: c.id, digest: c.digest }, "Approved for 30 minutes. The change applies when the session runs `harness apply`.") })
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
  return body;
}

export function renderChanges(ctx: Ctx): HTMLElement {
  const rows = ctx.snap.views.changes;
  const live = rows.filter((c) => !c.superseded);
  const old = rows.filter((c) => c.superseded);
  const showOld = ctx.ui.expanded.has(SUPERSEDED_KEY);
  const cols = [{ label: "Change" }, { label: "Status" }, { label: "Asked by" }, { label: "Asked" }, { label: "Applied" }, { label: "Actions", cls: "c-act" }];
  return h(
    "section",
    { class: "view" },
    viewHeader(ctx, "changes"),
    rows.length
      ? live.length
        ? dataTable(cols, changeRows(ctx, live), "Harness changes")
        : empty("Nothing waits for you.", "Every open change is superseded by a newer applied one.")
      : empty("No harness changes.", "A change shows here when a session asks to change the harness itself. It waits for your passkey tap."),
    old.length
      ? h(
          "div",
          { class: "superseded" },
          btn(`Superseded (${old.length})`, { tone: "quiet", ariaExpanded: showOld, onClick: () => ctx.toggle(SUPERSEDED_KEY), title: "Open requests that a newer applied change replaced" }),
          showOld ? dataTable(cols, changeRows(ctx, old), "Superseded harness changes") : null,
        )
      : null,
    mergeForm(ctx),
  );
}
