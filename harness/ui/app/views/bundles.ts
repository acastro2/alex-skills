import { h, sha, timeEl } from "../dom.ts";
import type { BundleRow, CommandRun, Ctx } from "../ctx.ts";
import { chip, dataTable, detailRow, empty, expandToggle, modelId, sessionLink, td, viewHeader, type Tone } from "../parts.ts";

function verdictChip(v: string | null) {
  const tone: Tone = v === "green" ? "green" : v === "red" ? "red" : "neutral";
  return chip(tone, v ?? "no verdict");
}

function runs(title: string, who: string, list: CommandRun[]): HTMLElement {
  return h(
    "div",
    { class: "runs" },
    h("h3", null, title, h("span", { class: "dim" }, ` ${who}`)),
    list.length
      ? h(
          "ul",
          { class: "run-list" },
          list.map((r) =>
            h(
              "li",
              null,
              h("span", { class: `exit ${r.exit === 0 ? "ok" : "bad"}`, title: "exit code" }, r.exit === null ? "exit ?" : `exit ${r.exit}`),
              h("code", { class: "mono" }, r.command),
              r.tail ? h("span", { class: "tail mono dim" }, r.tail) : null,
            ),
          ),
        )
      : h("p", { class: "dim" }, "None recorded."),
  );
}

export function renderBundles(ctx: Ctx): HTMLElement {
  const rows = ctx.snap.views.bundles;
  const body: HTMLElement[] = [];
  const cols = 6;
  for (const b of rows as BundleRow[]) {
    const key = `bundle:${b.id}`;
    const selected = ctx.route.id === b.id || ctx.route.id === b.head_sha;
    const open = ctx.ui.expanded.has(key) || selected;
    body.push(
      h(
        "tr",
        { class: `${selected ? "selected" : ""}${open ? " is-open" : ""}`, "data-selected": selected ? "true" : undefined, "aria-current": selected ? "true" : undefined },
        td("Verdict", null, verdictChip(b.verdict)),
        td("Head", "c-session", expandToggle(ctx, key, sha(b.head_sha), open, h("span", { class: "mono strong" }, sha(b.head_sha, 10)))),
        td("What it did", "c-goal", b.summary ?? h("span", { class: "dim" }, "No summary")),
        td("Session", null, h("span", { class: "stack" }, sessionLink(ctx, b.session_slug, b.session_id), b.worker_model ? modelId(b.worker_model) : null)),
        td("Push gate", null, b.gate ? chip(b.gate.outcome === "allow" || /pass/.test(b.gate.reason ?? "") ? "green" : "red", b.gate.reason ?? b.gate.outcome ?? "recorded") : h("span", { class: "dim" }, "not run")),
        td("Age", null, timeEl(b.time, ctx.now)),
      ),
    );
    if (open) {
      body.push(
        detailRow(
          cols,
          b.did.length ? h("div", { class: "runs" }, h("h3", null, "Changed"), h("ul", { class: "files mono" }, b.did.map((d) => h("li", null, d)))) : null,
          runs("Worker said", "(its own report)", b.works),
          runs("Harness re-ran", "(the proof)", b.verified),
          b.known_gaps ? h("div", { class: "runs" }, h("h3", null, "Known gaps"), h("p", null, b.known_gaps)) : h("div", { class: "runs" }, h("h3", null, "Known gaps"), h("p", { class: "dim" }, "None recorded.")),
          b.advisory !== null ? h("p", { class: "hint" }, `Advisory score ${b.advisory.toFixed(2)}. Advice only: it never decides the verdict.`) : null,
        ),
      );
    }
  }
  return h(
    "section",
    { class: "view" },
    viewHeader(ctx, "bundles"),
    rows.length
      ? dataTable([{ label: "Verdict" }, { label: "Head" }, { label: "What it did" }, { label: "Session" }, { label: "Push gate" }, { label: "Age" }], body, "Proof bundles by head SHA")
      : empty("No proof bundles yet.", "A bundle shows here when a worker finishes: what it changed, what it claimed, and what the harness re-ran."),
  );
}
