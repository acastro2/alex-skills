// Parse every ```mermaid block in each file. Needs mermaid@11.4.1 and jsdom@25.0.1:
// run `npm install mermaid@11.4.1 jsdom@25.0.1` in a temp dir, copy this file there, run `node mermaid_parse.mjs <file.md>...`.
import { JSDOM } from "jsdom"; import fs from "fs";
const dom = new JSDOM("<!doctype html><body></body>", { pretendToBeVisual: true });
globalThis.window = dom.window; globalThis.document = dom.window.document;
for (const k of ["Element","HTMLElement","Node","DocumentFragment","NodeFilter","SVGElement","DOMParser","navigator"]) { if (!(k in globalThis)) globalThis[k] = dom.window[k]; }
const { default: mermaid } = await import("mermaid");
mermaid.initialize({ startOnLoad: false });
for (const f of process.argv.slice(2)) {
  const t = fs.readFileSync(f, "utf8"); const blocks = [...t.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(m => m[1]);
  let bad = [];
  for (const [i, b] of blocks.entries()) { try { await mermaid.parse(b); } catch (e) { bad.push(`#${i+1}: ${String(e.message).split("\n").slice(0,3).join(" | ")}`); } }
  console.log(f.split("iteration-1/")[1], `${blocks.length - bad.length}/${blocks.length} parse`, bad.join(" ;; "));
}
