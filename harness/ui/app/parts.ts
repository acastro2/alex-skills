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
    h("div", { class: "view-title" }, h("a", { class: "back", href: hashFor("office"), "aria-label": "Back to the office" }, icon("back", 15), h("span", null, "Office")), h("h1", { id: "view-h" }, meta?.label ?? "Office")),
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
