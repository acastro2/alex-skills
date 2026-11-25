// Builds the office figure: dist/office.js (ESM, no deps), dist/office.css, demo.html.
// Run from the repo root:  bun harness/ui/office/build.mjs
//
// The anatomy kit is inlined into office.js, so the bundle has no imports. The pure
// model (harness/src/ui/office-model.ts) is not in office.js: the host calls officeState()
// and passes the result to mountOffice(). demo.html inlines the model so it runs standalone.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ISO_CSS } from "../../../anatomy/kit/iso-kit.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const KIT = join(HERE, "..", "..", "..", "anatomy", "kit");
const read = (p) => readFileSync(p, "utf8");

// Turn a kit module into a function scope that returns its exports.
function scope(name, file, head = "") {
  const src = read(join(KIT, file)).replace(/^import .*$/gm, "");
  const names = [...src.matchAll(/^export (?:async )?(?:function|const|let|class)\s+(\w+)/gm)].map((m) => m[1]);
  const body = src.replace(/^export /gm, "");
  return `const ${name} = (() => {\n${head}${body}\nreturn { ${names.join(", ")} };\n})();\n`;
}

const kit = scope("k", "iso-kit.mjs") + scope("G", "lathe.mjs", "const { cameraOf, iso, pathOf } = k;\n") + scope("T", "tube.mjs", "const { iso, pathOf } = k;\n");
const geometry = read(join(HERE, "geometry.mjs")).replace(/^export /gm, "");
const live = read(join(HERE, "live.mjs"));

const bundle = `// Office figure. Built by harness/ui/office/build.mjs. Do not edit.\n${kit}${geometry}\n${live}`;
const css = `${ISO_CSS}\n${read(join(HERE, "office.css"))}`;

mkdirSync(join(HERE, "dist"), { recursive: true });
writeFileSync(join(HERE, "dist", "office.js"), bundle);
writeFileSync(join(HERE, "dist", "office.css"), css);

// ---- demo.html: one file, no server needed ----------------------------------------------------
const model = new Bun.Transpiler({ loader: "ts" }).transformSync(read(join(HERE, "..", "..", "src", "ui", "office-model.ts"))).replace(/^export /gm, "");
const fixture = read(join(HERE, "fixture.mjs")).replace(/^export /gm, "");
const page = `
const Q = Object.assign({}, window.__DEMO, Object.fromEntries(new URLSearchParams(location.search)));
const THEME = Q.theme === "light" ? "light" : "dark";
let step = Number(Q.step || 0);
const NOW0 = Date.now();
const stage = document.querySelector("#office");
const log = document.querySelector("#log");
const nextBtn = document.querySelector("#next");
const themeBtn = document.querySelector("#theme");
let model = officeState(fixtureAt(step, NOW0));
const office = mountOffice(stage, model, {
  theme: THEME,
  onSelect(target) { log.textContent = "onSelect: " + JSON.stringify(target); },
});
document.body.dataset.theme = THEME;
const label = () => { nextBtn.textContent = "Next change: " + CHANGES[step % CHANGES.length].name; };
label();
nextBtn.addEventListener("click", () => {
  step += 1;
  model = officeState(fixtureAt(step, NOW0 + step * 1000), model);
  office.update(model);
  label();
});
themeBtn.addEventListener("click", () => {
  const t = document.body.dataset.theme === "dark" ? "light" : "dark";
  document.body.dataset.theme = t;
  office.setTheme(t);
});
window.__office = { office, get model() { return model; } };
`;
// An inline script ends at the first closing script tag, so no literal one may stay inside it.
const inline = [bundle.replace(/^export /gm, ""), model, fixture, page].join("\n").replace(/<\/(script)/gi, "<\\/$1");
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Harness office (demo)</title><style>${css}
*{box-sizing:border-box}
body{margin:0;background:var(--anatomy-page);color:var(--anatomy-text);font:14px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
body[data-theme="dark"]{color-scheme:dark}body[data-theme="light"]{color-scheme:light}
main{width:min(1240px,100% - 24px);margin:20px auto 40px}
.bar{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center;margin:0 0 6px}
button{font:inherit;color:var(--anatomy-strong);background:var(--anatomy-card);border:1px solid var(--anatomy-mid);padding:6px 12px;cursor:pointer}
button:hover{border-color:var(--anatomy-hi)}button:focus-visible{outline:2px solid var(--anatomy-lit);outline-offset:2px}
#log{font:12px var(--anatomy-mono);color:var(--anatomy-muted);min-height:1.5em}
</style></head><body class="iso" data-theme="dark"><main>
<div class="bar"><button id="next" type="button"></button><button id="theme" type="button">Toggle theme</button><span id="log" role="status">Click a part, or Tab to one and press Enter.</span></div>
<div id="office"></div></main>
<script type="module">
${inline}
</script></body></html>`;
writeFileSync(join(HERE, "demo.html"), html);
console.log(`dist/office.js ${bundle.length} bytes, dist/office.css ${css.length} bytes, demo.html ${html.length} bytes`);
