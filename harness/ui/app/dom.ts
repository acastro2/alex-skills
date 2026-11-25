// A tiny element builder. Text always goes in as text nodes, never as HTML.
export type Child = Node | string | number | null | undefined | false | Child[];
type Props = Record<string, unknown> | null;

const SVG_NS = "http://www.w3.org/2000/svg";

function append(parent: Node, kids: Child[]): void {
  for (const k of kids) {
    if (k === null || k === undefined || k === false) continue;
    if (Array.isArray(k)) append(parent, k);
    else parent.appendChild(typeof k === "object" ? k : document.createTextNode(String(k)));
  }
}

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, props?: Props, ...kids: Child[]): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props ?? {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = String(v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2).toLowerCase(), v as EventListener);
    else if (k === "value" || k === "checked" || k === "disabled" || k === "selected") (el as unknown as Record<string, unknown>)[k] = v;
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  append(el, kids);
  return el;
}

const ICONS: Record<string, string> = {
  office: "M3 20V8l9-5 9 5v12M3 20h18M9 20v-6h6v6M8 10h.01M12 10h.01M16 10h.01",
  inbox: "M3 13l3-8h12l3 8v6H3zM3 13h5l1 3h6l1-3h5",
  sessions: "M4 5h16v11H4zM8 20h8M12 16v4M7 9l3 2-3 2M12 13h4",
  worktrees: "M6 3v12M6 15a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 9c0 4-6 3-12 6",
  bundles: "M12 3l8 4v10l-8 4-8-4V7zM4 7l8 4 8-4M12 11v10M8.5 13.5l2 1.5 4-4",
  rules: "M4 7h10M18 7h2M4 17h2M10 17h10M14 4v6M8 14v6",
  journal: "M6 3h12v18H6zM9 8h6M9 12h6M9 16h4",
  changes: "M7 4a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM7 8v8M7 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM17 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM17 16V9a3 3 0 0 0-3-3h-3M13 3l-2 3 2 3",
  jobs: "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM12 8v4l3 2",
  bell: "M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 21h4",
  sun: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  moon: "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z",
  auto: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 3v18",
  out: "M10 4H5v16h5M14 8l4 4-4 4M18 12H9",
  back: "M10 6l-6 6 6 6M4 12h16",
  chevron: "M9 6l6 6-6 6",
  key: "M8 14a4 4 0 1 1 3.4-6H21v3h-3v3h-3v-3h-3.6A4 4 0 0 1 8 14z",
  check: "M5 12l5 5 9-10",
  alert: "M12 3l10 18H2zM12 10v5M12 18h.01",
};

export function icon(name: string, size = 16): SVGSVGElement {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", String(size));
  svg.setAttribute("height", String(size));
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("class", "icon");
  const p = document.createElementNS(SVG_NS, "path");
  p.setAttribute("d", ICONS[name] ?? ICONS.alert);
  svg.appendChild(p);
  return svg;
}

export function clear(el: Element): void {
  while (el.firstChild) el.removeChild(el.firstChild);
}

const pad = (n: number) => String(n).padStart(2, "0");

export function clock(ms: number): string {
  const d = new Date(ms);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export function dayClock(ms: number, now: number): string {
  const d = new Date(ms);
  const same = new Date(now).toDateString() === d.toDateString();
  return same ? clock(ms) : `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** "just now", "4m", "2h 5m", "3d". Past or future. */
export function span(ms: number): string {
  const s = Math.floor(Math.abs(ms) / 1000);
  if (s < 45) return "now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m`;
  const hr = Math.floor(m / 60);
  if (hr < 24) return m % 60 ? `${hr}h ${m % 60}m` : `${hr}h`;
  return `${Math.floor(hr / 24)}d`;
}

export function ago(ts: number | null, now: number): string {
  if (ts === null || ts === undefined) return "never";
  const d = now - ts;
  return Math.abs(d) < 45_000 ? "just now" : d >= 0 ? `${span(d)} ago` : `in ${span(d)}`;
}

/** A <time> that the page refreshes in place, so a view never re-renders just to age a label. */
export function timeEl(ts: number | null, now: number, mode: "ago" | "clock" = "ago"): HTMLElement {
  if (ts === null || ts === undefined) return h("span", { class: "dim" }, "never");
  const text = mode === "ago" ? ago(ts, now) : dayClock(ts, now);
  return h("time", { datetime: new Date(ts).toISOString(), "data-ts": ts, "data-mode": mode, title: new Date(ts).toLocaleString() }, text);
}

export function refreshTimes(root: ParentNode, now: number): void {
  for (const t of root.querySelectorAll<HTMLElement>("time[data-ts]")) {
    const ts = Number(t.dataset.ts);
    const next = t.dataset.mode === "clock" ? dayClock(ts, now) : ago(ts, now);
    if (t.textContent !== next) t.textContent = next;
  }
}

export function mmss(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s >= 3600) return `${Math.floor(s / 3600)}h ${pad(Math.floor((s % 3600) / 60))}m`;
  return `${pad(Math.floor(s / 60))}:${pad(s % 60)}`;
}

export function firstLine(text: string | null | undefined, max = 160): string {
  if (!text) return "";
  const line = text.split("\n").find((l) => l.trim()) ?? "";
  const t = line.trim();
  return t.length > max ? `${t.slice(0, max - 1)}…` : t;
}

export function sha(s: string | null | undefined, n = 8): string {
  return s ? s.slice(0, n) : "none";
}
