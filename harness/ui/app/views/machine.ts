// The Machine view: how hard this VM is working. Reads `snap.resources` (see src/serve/resources.ts).
// Amber and red come from the server (`tone`, `reasons`); this file adds no thresholds of its own.
import { h, timeEl } from "../dom.ts";
import type { Ctx, ProcSample, Resources } from "../ctx.ts";
import { hashFor } from "../ctx.ts";
import { chip, empty, lineChart, viewHeader, type Tone } from "../parts.ts";

// ---------------------------------------------------------------- shared formats (the dashboard panel uses them too)

export const fmtPct = (n: number | null | undefined, digits = 0): string => (n === null || n === undefined ? "n/a" : `${n.toFixed(digits)} %`);
export const fmtMem = (mb: number): string => (mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${Math.round(mb)} MB`);
export const fmtGb = (gb: number): string => `${gb.toFixed(gb < 10 ? 1 : 0)} GB`;
const fmtRate = (n: number): string => `${n.toFixed(n < 10 ? 1 : 0)} MB/s`;

export const toneChip = (r: Resources): HTMLElement => chip(r.tone === "ok" ? "neutral" : (r.tone as Tone), r.tone === "ok" ? "Within limits" : r.tone === "amber" ? "Needs a look" : "Over limit");

/** The server's reasons, as one wash line under a header. Nothing when the machine is within limits. */
export function reasonsBox(r: Resources): HTMLElement | null {
  if (r.tone === "ok" || !r.reasons.length) return null;
  return h("ul", { class: `mach-reasons mach-${r.tone}`, "aria-label": "Why the machine is flagged" }, r.reasons.map((t) => h("li", null, t)));
}

const num = (n: number | null): number[] => (n === null ? [] : [n]);
export const memPct = (r: Resources): number | null => (r.memory ? (r.memory.total_mb ? (r.memory.used_mb / r.memory.total_mb) * 100 : null) : r.series[r.series.length - 1]?.mem ?? null);
export const peak = (values: (number | null)[]): number => Math.max(0, ...values.flatMap(num));

// ---------------------------------------------------------------- parts

function plate(title: string, meta: string | null, ...body: (Node | null)[]): HTMLElement {
  const id = `mh-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return h("section", { class: "panel mach-plate", "aria-labelledby": id }, h("header", { class: "ph" }, h("h2", { class: "ph-title", id }, title), meta ? h("span", { class: "ph-meta" }, meta) : null), h("div", { class: "pb" }, ...body));
}

const meter = (frac: number, label: string): HTMLElement =>
  h("span", { class: "meter", role: "img", "aria-label": label }, h("span", { class: "meter-fill", style: `width:${Math.max(0, Math.min(1, frac)) * 100}%` }));

const note = (text: string): HTMLElement => h("p", { class: "pb-empty dim" }, text);

function row(label: string, value: string, bar?: HTMLElement, sub?: string): HTMLElement {
  return h("li", { class: "mach-row" }, h("span", { class: "mach-k" }, label), h("span", { class: "mach-v mono" }, value), bar ?? null, sub ? h("span", { class: "mach-sub dim" }, sub) : null);
}

function chartPlate(title: string, values: (number | null)[], now: number | null, what: string): HTMLElement {
  const pk = peak(values);
  const chart = h(
    "div",
    { class: "mach-chart" },
    h("div", { class: "mach-y mono dim", "aria-hidden": "true" }, h("span", null, "100 %"), h("span", null, "50 %"), h("span", null, "0 %")),
    lineChart(values, { grid: true, label: `${what} over the last 60 minutes. Peak ${pk.toFixed(0)} percent. Now ${now === null ? "not known" : `${now.toFixed(0)} percent`}.` }),
  );
  return plate(title, `now ${fmtPct(now)}`, chart, h("div", { class: "mach-axis mono dim" }, h("span", null, "60 min ago"), h("span", null, `peak ${fmtPct(pk)}`), h("span", null, "now")));
}

function procTable(rows: ProcSample[], caption: string): HTMLElement {
  if (!rows.length) return note("No processes in this list yet.");
  const cols: [string, boolean][] = [["PID", true], ["CPU %", true], ["RSS MB", true], ["Elapsed", false], ["Command", false], ["Session", false]];
  return h(
    "table",
    { class: "dt" },
    h("caption", { class: "sr" }, caption),
    h("thead", null, h("tr", null, cols.map(([t, right]) => h("th", { scope: "col", class: right ? "num" : undefined }, t)))),
    h(
      "tbody",
      null,
      rows.map((p) =>
        h(
          "tr",
          null,
          h("td", { class: "num mono" }, String(p.pid)),
          h("td", { class: "num mono" }, p.cpu.toFixed(1)),
          h("td", { class: "num mono" }, String(Math.round(p.rss_mb))),
          h("td", { class: "mono" }, p.etime),
          h("td", { class: "mono cmd", title: p.args || p.comm }, p.args || p.comm),
          h("td", null, p.session ? h("a", { class: "mono link", href: hashFor("sessions", p.session) }, p.slug ?? p.session.slice(-6)) : h("span", { class: "dim" }, "none")),
        ),
      ),
    ),
  );
}

// ---------------------------------------------------------------- panels

function cores(r: Resources): HTMLElement {
  const list = r.cpu.cores;
  return plate(
    "CPU cores",
    `${r.cpu.count} ${r.cpu.count === 1 ? "core" : "cores"}`,
    list.length
      ? h("ul", { class: "mach-cores" }, list.map((c, i) => h("li", { class: "mach-core" }, h("span", { class: "mach-k mono" }, `cpu ${i}`), meter((c ?? 0) / 100, `Core ${i}: ${fmtPct(c)}`), h("span", { class: "mach-v mono" }, fmtPct(c)))))
      : note("The sampler gave no per-core numbers."),
  );
}

function load(r: Resources): HTMLElement {
  if (!r.load) return plate("Load average", null, note("Load average is not reported on this machine."));
  const n = Math.max(1, r.cpu.count);
  const items: [string, number][] = [["1 min", r.load.one], ["5 min", r.load.five], ["15 min", r.load.fifteen]];
  return plate(
    "Load average",
    `${r.cpu.count} ${r.cpu.count === 1 ? "core" : "cores"}`,
    h("ul", { class: "mach-rows" }, items.map(([k, v]) => row(k, v.toFixed(2), meter(v / n, `Load ${k}: ${v.toFixed(2)} on ${n} cores`), `${(v / n).toFixed(2)} a core`))),
    h("p", { class: "hint mach-hint" }, "A load above the core count means tasks wait for a core."),
  );
}

function memory(r: Resources): HTMLElement {
  const m = r.memory;
  if (!m) return plate("Memory", null, note("Memory is not reported on this machine."));
  const used = m.total_mb ? m.used_mb / m.total_mb : 0;
  return plate(
    "Memory",
    `${fmtMem(m.total_mb)} in all`,
    h(
      "ul",
      { class: "mach-rows" },
      row("Used", fmtMem(m.used_mb), meter(used, `Memory used: ${fmtPct(used * 100)}`), fmtPct(used * 100)),
      row("Available", fmtMem(m.available_mb), undefined, fmtPct(m.available_pct)),
      m.swap_total_mb > 0 ? row("Swap used", fmtMem(m.swap_used_mb), meter(m.swap_pct / 100, `Swap used: ${fmtPct(m.swap_pct)}`), `${fmtPct(m.swap_pct)} of ${fmtMem(m.swap_total_mb)}`) : row("Swap", "none", undefined, "This machine has no swap."),
    ),
  );
}

function disks(r: Resources): HTMLElement {
  if (!r.disks.length) return plate("Disks", null, note("No disks reported."));
  const rows = [...r.disks].sort((a, b) => b.used_pct - a.used_pct);
  return plate(
    "Disks",
    `${rows.length} ${rows.length === 1 ? "mount" : "mounts"}`,
    h(
      "table",
      { class: "dt" },
      h("caption", { class: "sr" }, "Disk use by mount"),
      h("thead", null, h("tr", null, [["Mount", false], ["Used %", true], ["", false], ["Used", true], ["Free", true]].map(([t, right]) => h("th", { scope: "col", class: right ? "num" : undefined }, t as string)))),
      h(
        "tbody",
        null,
        rows.map((d) =>
          h(
            "tr",
            null,
            h("td", { class: "mono cmd", title: d.mount }, d.mount),
            h("td", { class: "num mono" }, fmtPct(d.used_pct)),
            h("td", { class: "mach-bar-cell" }, meter(d.used_pct / 100, `${d.mount}: ${fmtPct(d.used_pct)} used`)),
            h("td", { class: "num mono" }, fmtGb(d.used_gb)),
            h("td", { class: "num mono" }, fmtGb(d.free_gb)),
          ),
        ),
      ),
    ),
  );
}

function io(r: Resources): HTMLElement {
  if (!r.io) return plate("Disk IO", null, note("Disk IO is not reported on this machine."));
  return plate("Disk IO", "since the last sample", h("ul", { class: "mach-rows" }, row("Read", fmtRate(r.io.read_mb_s)), row("Write", fmtRate(r.io.write_mb_s))));
}

function pressure(r: Resources): HTMLElement {
  if (!r.pressure) return plate("Pressure", null, note("Pressure is not reported on this machine."));
  const p = r.pressure;
  return plate(
    "Pressure",
    "last 10 seconds",
    h("ul", { class: "mach-rows" }, row("CPU", fmtPct(p.cpu, 1)), row("Memory", fmtPct(p.memory, 1)), row("Disk IO", fmtPct(p.io, 1))),
    h("p", { class: "hint mach-hint" }, "The share of time at least one task waited for that resource."),
  );
}

// ---------------------------------------------------------------- entry

export function renderMachine(ctx: Ctx): HTMLElement {
  const r = ctx.snap.resources ?? null;
  if (!r) {
    return h("section", { class: "view mach", "aria-labelledby": "view-h" }, viewHeader(ctx, "machine"), empty("No samples yet.", "The machine sampler has not reported. The charts and tables show here after its first sample."));
  }
  const cpu = r.series.map((p) => p.cpu);
  const mem = r.series.map((p) => p.mem);
  return h(
    "section",
    { class: "view mach", "aria-labelledby": "view-h" },
    viewHeader(ctx, "machine", h("span", { class: "mach-tools" }, toneChip(r), h("span", null, "Sampled ", timeEl(r.at, ctx.now)), r.source === "macos-fallback" ? h("span", null, "macOS numbers are approximate.") : null)),
    reasonsBox(r),
    h("div", { class: "mach-row-2" }, chartPlate("CPU use", cpu, r.cpu.total, "CPU use"), chartPlate("Memory use", mem, memPct(r), "Memory use")),
    h("div", { class: "mach-row-3" }, cores(r), load(r), memory(r)),
    h("div", { class: "mach-row-3" }, disks(r), io(r), pressure(r)),
    h("div", { class: "mach-row-2" }, plate("Top processes by CPU", `${r.top_cpu.length} shown`, procTable(r.top_cpu, "Processes using the most CPU")), plate("Top processes by memory", `${r.top_rss.length} shown`, procTable(r.top_rss, "Processes using the most memory"))),
  );
}
