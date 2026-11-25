// Parts every working view shares: one vocabulary, so the same thing looks the same in each view.
import type { Child } from "./dom.ts";
import { h, icon } from "./dom.ts";
import type { Ctx, SessionRow, ViewName } from "./ctx.ts";
import { hashFor, VIEWS } from "./ctx.ts";

export type Tone = "neutral" | "amber" | "red" | "green" | "ink";

export function chip(tone: Tone, text: string): HTMLElement {
  return h("span", { class: `chip chip-${tone}` }, text);
}

export function viewHeader(ctx: Ctx, view: ViewName, extra?: Child): HTMLElement {
  const meta = VIEWS.find((v) => v.id === view);
  return h(
    "header",
    { class: "view-head" },
    h("div", { class: "view-title" }, h("a", { class: "back", href: hashFor("office"), "aria-label": "Back to the dashboard" }, icon("back", 15), h("span", null, "Dashboard")), h("h1", { id: "view-h" }, meta?.label ?? "Dashboard")),
    h("p", { class: "view-blurb" }, meta?.blurb ?? ""),
    extra ? h("div", { class: "view-tools" }, extra) : null,
  );
}

/** Empty state: say what will appear here, and why. */
export function empty(title: string, why: string): HTMLElement {
  return h("div", { class: "empty" }, h("p", { class: "empty-title" }, title), h("p", { class: "empty-why" }, why));
}

export function skeleton(rows = 5): HTMLElement {
  return h(
    "div",
    { class: "skeleton", "aria-busy": "true", "aria-label": "Loading" },
    Array.from({ length: rows }, (_, i) => h("div", { class: "skeleton-row" }, h("span", { class: "sk sk-a" }), h("span", { class: `sk sk-b${i % 3}` }), h("span", { class: "sk sk-c" }))),
  );
}

export function sessionLink(ctx: Ctx, slug: string | null, id: string | null): Child {
  if (!id) return h("span", { class: "dim" }, "none");
  return h("a", { class: "mono link", href: hashFor("sessions", id) }, slug ?? id.slice(-6));
}

export function journalLink(session: string, label = "Journal"): HTMLElement {
  return h("a", { class: "btn btn-quiet", href: hashFor("journal", null, { session }) }, label);
}

export function stateChip(s: SessionRow): HTMLElement {
  const map: Record<string, [Tone, string]> = {
    waiting: ["amber", "waiting for you"],
    stuck: ["amber", "stuck"],
    running: ["ink", "running"],
    idle: ["neutral", "idle"],
    ended: ["neutral", "ended"],
  };
  const [tone, text] = map[s.state] ?? ["neutral", s.state];
  return chip(tone, text);
}

export interface BtnOpts {
  tone?: "default" | "primary" | "danger" | "quiet";
  disabled?: boolean;
  busy?: boolean;
  title?: string;
  onClick?: (e: MouseEvent) => void;
  icon?: string;
  type?: "button" | "submit";
  ariaExpanded?: boolean;
}

export function btn(label: string, o: BtnOpts = {}): HTMLButtonElement {
  return h(
    "button",
    {
      type: o.type ?? "button",
      class: `btn btn-${o.tone ?? "default"}${o.busy ? " is-busy" : ""}`,
      disabled: o.disabled || o.busy,
      title: o.title,
      "aria-busy": o.busy ? "true" : undefined,
      "aria-expanded": o.ariaExpanded === undefined ? undefined : String(o.ariaExpanded),
      onClick: o.onClick,
    },
    o.icon ? icon(o.icon, 14) : null,
    h("span", null, label),
  );
}

export interface Col {
  label: string;
  cls?: string;
}

export function dataTable(cols: Col[], body: HTMLElement[], caption: string): HTMLTableElement {
  return h(
    "table",
    { class: "grid" },
    h("caption", { class: "sr" }, caption),
    h("thead", null, h("tr", null, cols.map((c) => h("th", { scope: "col", class: c.cls }, c.label)))),
    h("tbody", null, body),
  );
}

export function td(label: string, cls: string | null, ...kids: Child[]): HTMLTableCellElement {
  return h("td", { "data-label": label, class: cls }, ...kids);
}

/** A row that opens a detail row under it. The first cell holds the toggle button. */
export function expandToggle(ctx: Ctx, key: string, label: string, open: boolean, content: Child): HTMLButtonElement {
  return h(
    "button",
    { type: "button", class: "twisty", "aria-expanded": String(open), "aria-label": `Details: ${label}`, onClick: () => ctx.toggle(key) },
    icon("chevron", 14),
    h("span", { class: "twisty-text" }, content),
  );
}

export function detailRow(cols: number, ...kids: Child[]): HTMLTableRowElement {
  return h("tr", { class: "detail" }, h("td", { colspan: String(cols) }, h("div", { class: "detail-box" }, ...kids)));
}

export function kv(pairs: [string, Child][]): HTMLElement {
  return h("dl", { class: "kv" }, pairs.flatMap(([k, v]) => [h("dt", null, k), h("dd", null, v)]));
}

/** A model id like `cursor/claude-haiku-5-5`: it may break after a `/`, never inside a name. */
export function modelId(id: string): HTMLElement {
  const parts = id.split("/")
  const kids: Child[] = []
  parts.forEach((p, i) => {
    kids.push(h("span", null, i < parts.length - 1 ? `${p}/` : p))
    if (i < parts.length - 1) kids.push(h("wbr"))
  })
  return h("span", { class: "dim mono block model" }, ...kids)
}

const SVG_NS = "http://www.w3.org/2000/svg";

/**
 * A line chart over the last 60 minutes, one slot a minute, newest on the right. A null value breaks the line.
 * The x axis is fixed at 60 slots, so a young series fills from the right and the empty left side is honest.
 */
export function lineChart(values: (number | null)[], o: { label: string; max?: number; grid?: boolean; slots?: number }): SVGSVGElement {
  const slots = o.slots ?? 60;
  const max = o.max ?? 100;
  const last = slots - 1;
  const el = (name: string, attrs: Record<string, string>) => {
    const n = document.createElementNS(SVG_NS, name);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    return n;
  };
  const svg = el("svg", { viewBox: `0 0 ${last} 100`, preserveAspectRatio: "none", class: "lc", role: "img", "aria-label": o.label }) as SVGSVGElement;
  if (o.grid) for (const y of [25, 50, 75]) svg.append(el("line", { x1: "0", x2: String(last), y1: String(y), y2: String(y), class: "lc-grid" }));
  const pts = values.slice(-slots).map((v, i, a) => (v === null ? null : [last - (a.length - 1 - i), 100 - Math.max(0, Math.min(max, v)) / max * 100] as [number, number]));
  let run: [number, number][] = [];
  const flush = () => {
    if (run.length) {
      const d = run.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(2)} ${y.toFixed(2)}`).join(" ");
      svg.append(el("path", { d: `${d} L${run[run.length - 1][0]} 100 L${run[0][0]} 100 Z`, class: "lc-area" }), el("path", { d, class: "lc-line" }));
    }
    run = [];
  };
  for (const p of pts) {
    if (p) run.push(p);
    else flush();
  }
  flush();
  return svg;
}
