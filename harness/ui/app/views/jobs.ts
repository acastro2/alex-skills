import { h, timeEl } from "../dom.ts";
import type { Ctx, JobRow } from "../ctx.ts";
import { btn, chip, dataTable, empty, td, viewHeader, type Tone } from "../parts.ts";

const RESULT: Record<JobRow["result"], [Tone, string]> = { ok: ["green", "ok"], failed: ["red", "failed"], never: ["neutral", "never run"], unknown: ["neutral", "unknown"] };

export function renderJobs(ctx: Ctx): HTMLElement {
  const rows = ctx.snap.views.jobs;
  const body = rows.map((j) => {
    const selected = ctx.route.id === j.name;
    const key = `job:${j.name}`;
    const [tone, text] = RESULT[j.result];
    return h(
      "tr",
      { class: selected ? "selected" : "", "data-selected": selected ? "true" : undefined, "aria-current": selected ? "true" : undefined },
      td("Job", "c-session", h("span", { class: "mono strong" }, j.name)),
      td("Schedule", null, h("span", { class: "mono" }, j.schedule ?? "none")),
      td("Last run", null, timeEl(j.last_run_at, ctx.now)),
      td("Result", null, chip(tone, text), j.last_result && j.result !== "never" ? h("span", { class: "dim block" }, j.last_result) : null),
      td("Next run", null, j.next_run_at ? timeEl(j.next_run_at, ctx.now) : h("span", { class: "dim" }, "not scheduled")),
      td("", "c-act", btn("Run now", { busy: ctx.ui.pending.has(key), onClick: () => void ctx.act(key, "run-job", { name: j.name }, `${j.name}: run requested.`) })),
    );
  });
  return h(
    "section",
    { class: "view" },
    viewHeader(ctx, "jobs"),
    rows.length
      ? dataTable([{ label: "Job" }, { label: "Schedule" }, { label: "Last run" }, { label: "Result" }, { label: "Next run" }, { label: "Actions", cls: "c-act" }], body, "Scheduled jobs")
      : empty("No jobs scheduled.", "Jobs show here once the harness registers its cron jobs, such as the correction miner."),
  );
}
