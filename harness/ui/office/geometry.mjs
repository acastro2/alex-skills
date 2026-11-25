// The office floor as solids. Pure: kit namespaces in, SVG strings out. The page rebuilds
// every moving part from this same module (the arcade-cabinet pattern), so the build and
// the live figure draw the same drawing.
//
// World: x and y on the floor, z up. Two walls at the back (y = 0 and x = 0). Row A of
// desks stands against the y wall, row B against the x wall. Each desk is drawn in a local
// frame: u runs along the row, v runs away from the wall.

export function makeOffice(k, G, T) {
  const W = 470;
  const D = 470;
  const WALL = 176;
  const VBW = 1180;
  const VBH = 880;
  const P = k.fitProjection(k.boxCorners({ x: -6, y: -6, w: W + 6, d: D + 6 }, -4, WALL), VBW, VBH, { pad: 12 });

  const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const iso = (p) => k.iso(p, P);
  const S = (paths, style) => k.solidSvg(paths, style);
  const L = (d, style) => k.lineSvg(d, style);
  const seg = (a, b) => k.segment(a, b, P);
  const poly = (pts, closed = false) => k.pathOf(pts.map(iso), closed);
  const dep = (p) => k.depthOf(p, P);
  const slab = (plan, z, h, style = {}, steps = 3, bevel = 0) => S(k.slabOf(plan, z, h, P, steps, bevel), style);
  const cyl = (cx, cy, r, z, h, style = {}, steps = 20) => S(k.cylinder(cx, cy, r, z, h, P, steps), style);
  const clip = (t, n) => (t.length > n ? `${t.slice(0, Math.max(1, n - 1))}…` : t);
  const fmtTime = (ms) => new Date(ms).toTimeString().slice(0, 5);

  // Hit outline: the hull of a box, drawn only when the target has focus or the pointer.
  const hit = (pts) => `<path class="of-hit" d="${k.pathOf(G.hullOf(pts.map(iso)), true)}"/>`;
  const boxHit = (b, z0, z1, g = 1.6) => hit(k.boxCorners({ x: b.x - g, y: b.y - g, w: b.w + g * 2, d: b.d + g * 2 }, z0 - g, z1 + g));
  const target = (kind, id, label, inner, hitSvg, extra = "") =>
    `<g class="of-target" data-kind="${kind}"${id ? ` data-id="${esc(id)}"` : ""} tabindex="0" role="button" aria-label="${esc(label)}"${extra}>${hitSvg.replace('class="of-hit"', 'class="of-hit-fill"')}${inner}${hitSvg}</g>`;

  const rect3 = (x0, x1, z0, z1, y) => poly([[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]], true);

  // ---- rows and desks -------------------------------------------------------------------
  const PITCH = 98;
  function frame(slot) {
    if (slot < 4) {
      const x0 = 76 + slot * PITCH;
      return {
        row: "A",
        pt: (u, v, z = 0) => [x0 + u, v, z],
        plan: (u, v, w, d, r = 1) => ({ x: x0 + u, y: v, w, d, r }),
        text: (u, v, z) => k.sideMatrix([x0 + u, v], z, P, "left"),
      };
    }
    const y0 = 170 + (slot - 4) * PITCH;
    return {
      row: "B",
      pt: (u, v, z = 0) => [v, y0 - u, z],
      plan: (u, v, w, d, r = 1) => ({ x: v, y: y0 - u - w, w: d, d: w, r }),
      text: (u, v, z) => k.sideMatrix([v, y0 - u], z, P, "right"),
    };
  }

  const FACE = (f, u, v, z, w, h, id, uid) => {
    // The screen plane: origin at its top-left, local v runs down.
    const m = f.text(u, v, z);
    const cid = `of${uid}-${id}`;
    return {
      m,
      cid,
      defs: `<clipPath id="${cid}"><path transform="${m}" d="M0 0H${w}V${h}H0Z"/></clipPath>`,
      back: `<path class="of-screen" transform="${m}" d="M0 0H${w}V${h}H0Z"/>`,
      text: (s, x, y, size, tone) => `<text class="iso-face-text of-t" data-tone="${tone}" transform="${m}" x="${x}" y="${y}" font-size="${size}">${esc(s)}</text>`,
      rect: (x, y, w2, h2, cls) => `<path class="${cls}" transform="${m}" d="M${x} ${y}h${w2}v${h2}h${-w2}Z"/>`,
    };
  };

  const ductRoute = (slot, side) => {
    const f = frame(slot);
    const u = side ? 80 : 5;
    return side
      ? [f.pt(u, 4.4, 81), f.pt(u, 4.4, 34), f.pt(u, 18, 34), f.pt(u, 18, 25.5)]
      : [f.pt(u, 4.4, 81), f.pt(u, 4.4, 46), f.pt(u, 33, 46), f.pt(u, 33, 30.5)];
  };
  const HUB = { x: 4, y: 4, w: 44, d: 44, r: 3 };
  const ductStart = (slot) => (slot < 4 ? [48, 4.4, 84] : [4.4, 48, 84]);
  /** The path a wake capsule follows: hub, along the duct, down the branch, into the tray. */
  function capsulePath(slot, side) {
    const f = frame(slot);
    const u = side ? 80 : 5;
    const top = f.pt(u, 4.4, 84);
    return G.fillet([ductStart(slot), top, ...ductRoute(slot, side).slice(1)], 6, 7);
  }

  function branch(slot, side) {
    const pts = G.fillet(ductRoute(slot, side), 5, 7);
    return T.tubePieces(pts, side ? 2 : 2.5, P, { maxLength: 12, caps: [false, true] }).map((piece) => ({ key: dep(piece.mid), svg: T.tubeSvg(piece, { tone: "mid" }) }));
  }

  const toolMark = (t) => (t === "claude" ? "CC" : "OC");

  /** One desk, plus its side desk when a worker sits beside it. */
  function desk(slot, d, sideD, uid, opts = {}) {
    const f = frame(slot);
    const free = !d;
    const dim = d?.dim;
    const first = [];
    const items = [];
    const add = (svg, p) => items.push({ key: dep(p), svg });
    const mid = (u, v, z) => f.pt(u, v, z);

    // top, ends, nameplate
    first.push(slab(f.plan(3, 12, 4, 36, 0.5), 0, 22, { tone: "mid" }, 2));
    first.push(slab(f.plan(55, 12, 4, 36, 0.5), 0, 22, { tone: "mid" }, 2));
    first.push(slab(f.plan(0, 10, 62, 40, 2), 22, 5, { tone: "mid" }, 3, 0.3));
    first.push(L(k.planOutline(k.insetPlan(f.plan(0, 10, 62, 40, 2), 2.2), 27, P, 3), { tone: "faint" }));
    const plate = f.text(3, 50.1, 24.8);
    const name = opts.empty ? "No sessions on this host" : free ? `desk ${slot + 1} · free` : `${toolMark(d.tool)} · ${d.slug}${d.repo ? ` · ${clip(d.repo, 12)}` : ""}`;
    first.push(k.faceTextSvg(plate, name, { size: 2.7, tone: free ? "lo" : "mid" }));

    // monitor
    add(cyl(...f.pt(41, 30).slice(0, 2), 7.5, 27, 1.2, { tone: "hi" }), mid(41, 30, 27));
    add(slab(f.plan(37.5, 28.4, 7, 4, 1), 28, 9, { tone: "hi" }, 2), mid(41, 30, 32));
    const lit = d?.lit && d.question ? false : d?.lit && d.stuck;
    const sw = 31;
    const sh = 20.5;
    const scr = FACE(f, 26.5, 33.2, 59.5, sw, sh, `d${slot}`, uid);
    let screen = scr.defs + scr.back;
    if (d) {
      const goal = d.goal ? clip(d.goal, 22) : "no goal set";
      let body = scr.text(`${toolMark(d.tool)} ${d.slug}${d.parent ? " ↳" : ""}`, 1.6, 4.4, 2.7, "mid");
      body += scr.text(`> ${goal}`, 1.6, 10.2, 3.1, "hi");
      body += scr.text(d.repo ? clip(d.repo, 24) : "no repo", 1.6, 15, 2.5, "lo");
      if (d.running && !d.ended) body += scr.rect(1.6, 16.6, 3.4, 2.4, "of-cursor");
      if (d.stuck && !d.ended) body += scr.text("STUCK", 1.6, 19.2, 2.8, "red");
      else if (d.question && !d.ended) body += scr.text("? ANSWER", 1.6, 19.2, 2.8, "hi");
      else if (d.ended) body += scr.text("ended", 1.6, 19.2, 2.6, "lo");
      screen += `<g clip-path="url(#${scr.cid})">${body}</g>`;
    } else {
      screen += `<g clip-path="url(#${scr.cid})">${scr.text("— free —", 1.6, 11, 3, "faint")}</g>`;
    }
    add(slab(f.plan(24, 27.5, 36, 5.7, 1.5), 36, 26, { tone: "hi", lit }, 3, 0.4) + screen, mid(42, 30, 49));

    // keyboard
    const kp = f.plan(26, 36, 32, 10, 1);
    const keys = [];
    for (let r = 0; r < 3; r++) for (let c = 0; c < 9; c++) keys.push(iso(f.pt(29 + c * 3.2, 38 + r * 2.8, 29)));
    add(slab(kp, 27, 2, { tone: "mid" }, 2) + k.dotsSvg(keys, { size: 0.45, tone: "mid" }), mid(42, 41, 28));

    // lamp
    const lampOn = d?.lamp;
    const lampCx = f.pt(14, 18);
    add(
      cyl(lampCx[0], lampCx[1], 3.2, 27, 1.4, { tone: "mid" }, 14) +
        L(seg(f.pt(14, 18, 28.4), f.pt(14, 18, 44)), { tone: "mid" }) +
        slab(f.plan(9, 14, 10, 9, 2), 44, 3.4, { tone: "mid" }, 2) +
        (lampOn
          ? L(poly([f.pt(10, 21, 44), f.pt(6, 30, 27.1)]) + poly([f.pt(14, 23, 44), f.pt(14, 31, 27.1)]) + poly([f.pt(18, 21, 44), f.pt(22, 30, 27.1)]), { tone: "green", dashed: true })
          : ""),
      mid(14, 18, 36),
    );

    // in-tray and card
    const trayPlan = f.plan(3, 30, 18, 16, 1);
    const cardPlan = f.plan(8, 36, 12, 1.6, 0.4);
    const trayBox = { x: Math.min(...[f.pt(3, 30)[0], f.pt(21, 46)[0]]), y: Math.min(f.pt(3, 30)[1], f.pt(21, 46)[1]), w: 16 + (f.row === "A" ? 2 : 0), d: 16 + (f.row === "A" ? 2 : 0) };
    const tray = slab(trayPlan, 27, 2.2, { tone: "mid" }, 2) + L(k.planOutline(k.insetPlan(trayPlan, 2), 29.2, P, 2), { tone: "faint" });
    const card = d?.tray ? slab(cardPlan, 29.2, 12, { tone: "hi", lit: d.lit && d.question }, 2) : "";
    const trayLabel = d ? `In-tray of session ${d.slug}: ${d.tray ? "a question waits" : "empty"}` : "In-tray: empty";
    const trayInner = tray + card;
    const trayHit = hit(k.boxCorners(trayPlan, 26, d?.tray ? 43 : 31).map((p) => p));
    add(d?.tray ? target("inbox", d.session, trayLabel, trayInner, trayHit) : trayInner, mid(12, 38, 30));

    // flag
    if (d) {
      add(L(seg(f.pt(59, 14, 27), f.pt(59, 14, 75)), { tone: "mid" }), mid(59, 14, 50));
      if (d.flag) add(slab(f.plan(44, 13.2, 15, 1.4, 0.4), 62, 9, { tone: "red", flat: false }, 2), mid(52, 14, 66));
    }

    for (const b of branch(slot, false)) items.push(b);

    let side = "";
    if (sideD) {
      const s = sideD;
      const sItems = [];
      const sAdd = (svg, p) => sItems.push({ key: dep(p), svg });
      const sFirst = [];
      sFirst.push(slab(f.plan(67.5, 16, 3, 28, 0.5), 0, 20, { tone: "mid" }, 2));
      sFirst.push(slab(f.plan(90.5, 16, 3, 28, 0.5), 0, 20, { tone: "mid" }, 2));
      sFirst.push(slab(f.plan(66, 14, 28, 32, 1.5), 20, 4, { tone: "mid" }, 3, 0.3));
      sFirst.push(k.faceTextSvg(f.text(68, 46.1, 22.6), `${toolMark(s.tool)} · ${s.slug} · worker`, { size: 2.2, tone: "mid" }));
      sAdd(cyl(...f.pt(80, 28).slice(0, 2), 4.4, 24, 1, { tone: "hi" }, 16), mid(80, 28, 24));
      const ssw = 17;
      const ssh = 13;
      const sc = FACE(f, 71.5, 31.7, 40.5, ssw, ssh, `s${slot}`, uid);
      let sscreen = sc.defs + sc.back;
      sscreen += `<g clip-path="url(#${sc.cid})">${sc.text(`> ${clip(s.goal || "no goal", 11)}`, 1.2, 5, 2.4, "hi")}${sc.text(clip(s.repo || "no repo", 14), 1.2, 9.2, 2.0, "lo")}${s.running && !s.ended ? sc.rect(1.2, 10, 2.6, 1.8, "of-cursor") : ""}${s.stuck ? sc.text("STUCK", 1.2, 12.4, 2.2, "red") : ""}</g>`;
      sAdd(slab(f.plan(69.5, 28.5, 21, 4.2, 1.2), 25, 18.5, { tone: "hi", lit: s.lit && s.stuck }, 3, 0.3) + sscreen, mid(80, 30, 34));
      sAdd(slab(f.plan(72, 36, 16, 7, 1), 24, 1.4, { tone: "mid" }, 2), mid(80, 40, 25));
      if (s.tray) {
        sAdd(
          target("inbox", s.session, `In-tray of worker ${s.slug}: a question waits`, slab(f.plan(75, 44.5, 10, 1.4, 0.4), 24, 9, { tone: "hi", lit: s.lit && s.question }, 2), hit(k.boxCorners(f.plan(74, 43.5, 12, 3.4), 23, 34))),
          mid(80, 45, 28),
        );
      }
      if (s.flag) sAdd(slab(f.plan(86, 17.4, 5, 1.2, 0.3), 44, 7, { tone: "red" }, 2), mid(88, 18, 48));
      for (const b of branch(slot, true)) sItems.push(b);
      side = sFirst.join("") + sItems.sort((a, b) => a.key - b.key).map((i) => i.svg).join("");
    }

    const sorted = items.sort((a, b) => a.key - b.key).map((i) => i.svg).join("");
    // A worker's desk sits in the same group: sort it in with its parent's items by depth.
    const body = first.join("") + sorted;
    const all = side ? mergeByDepth(first.join(""), items, side, sideD, f) : body;
    const outline = boxHitFor(f, sideD ? 96 : 64);
    let label = free ? `Desk ${slot + 1}: free` : d.label;
    if (opts.empty) label = "Desk 1: no sessions on this host";
    const dimClass = dim ? " of-dim" : "";
    const inner = `<g class="of-desk${dimClass}" data-slot="${slot}">${all}</g>`;
    return d ? target("session", d.session, label, inner, outline, ` data-slot="${slot}"`) : `<g class="of-free">${inner}</g>`;
  }

  // The side desk is a separate pile, drawn after the parent's loose items: they never overlap on screen.
  function mergeByDepth(firstSvg, items, sideSvg, sideD, f) {
    const sorted = items.sort((a, b) => a.key - b.key).map((i) => i.svg).join("");
    return firstSvg + sorted + sideSvg;
  }
  function boxHitFor(f, span) {
    const c = [];
    for (const u of [0, span]) for (const v of [10, 50]) for (const z of [0, 76]) c.push(f.pt(u, v, z));
    return hit(c);
  }

  // ---- the room -------------------------------------------------------------------------
  function room() {
    const out = [];
    out.push(slab({ x: 0, y: 0, w: W, d: D, r: 0 }, -4, 4, { tone: "lo", crease: "none" }, 2));
    const lines = [];
    for (let v = 47; v < W; v += 47) lines.push(k.lineOnTop([v, 0], [v, D], 0, P), k.lineOnTop([0, v], [W, v], 0, P));
    out.push(L(lines.join(""), { tone: "faint" }));
    out.push(slab({ x: -6, y: -6, w: W + 6, d: 6, r: 0 }, -4, WALL + 4, { tone: "lo", crease: "none" }, 2));
    out.push(slab({ x: -6, y: 0, w: 6, d: D, r: 0 }, -4, WALL + 4, { tone: "lo", crease: "none" }, 2));
    const ribs = [];
    for (let v = 47; v < W; v += 47) ribs.push(seg([v, 0, 60], [v, 0, WALL]), seg([0, v, 60], [0, v, WALL]));
    ribs.push(seg([0, 0, 60], [W, 0, 60]), seg([0, 0, 60], [0, D, 60]), seg([0, 0, 0], [0, 0, WALL]));
    out.push(L(ribs.join(""), { tone: "faint" }));
    out.push(slab({ x: 0, y: 0, w: W, d: 2.4, r: 0 }, 0, 7, { tone: "lo" }, 2));
    out.push(slab({ x: 0, y: 2.4, w: 2.4, d: D - 2.4, r: 0 }, 0, 7, { tone: "lo" }, 2));
    const rug = { x: 124, y: 96, w: 320, d: 330, r: 8 };
    out.push(slab(rug, 0, 0.8, { tone: "lo", crease: "none" }, 4));
    out.push(L(k.planOutline(k.insetPlan(rug, 6), 0.8, P, 4), { tone: "faint" }));
    out.push(L(k.planOutline(k.insetPlan(rug, 11), 0.8, P, 4), { tone: "faint", dotted: true }));
    return out.join("");
  }

  const sign = (host) => {
    const m = k.sideMatrix([0, 330], 138, P, "right");
    return `<text class="iso-face-text of-sign" data-tone="mid" transform="${m}" x="0" y="0" font-size="11">HOST</text><text class="iso-face-text of-sign" data-tone="hi" transform="${m}" x="0" y="14" font-size="13">${esc(host)}</text>${L(seg([0, 330, 110], [0, 262, 110]), { tone: "faint" })}`;
  };

  // ---- hub and ducts --------------------------------------------------------------------
  function hub(active) {
    const out = [slab(HUB, 0, 92, { tone: "hi" }, 3, 0.4)];
    out.push(slab({ x: 8, y: 8, w: 36, d: 36, r: 2 }, 92, 3, { tone: "mid" }, 2));
    const lamps = [];
    for (let i = 0; i < 5; i++) lamps.push(iso([10 + i * 7, 48.1, 80]), iso([48.1, 10 + i * 7, 80]));
    out.push(k.dotsSvg(lamps, { size: 0.9, tone: active ? "hi" : "faint" }));
    out.push(L(rect3(10, 42, 62, 72, 48.1), { tone: "mid" }));
    out.push(k.faceTextSvg(k.sideMatrix([11, 48.1], 70, P, "left"), "WAKER", { size: 3, tone: "hi" }));
    return out.join("");
  }
  function ducts() {
    const a = T.tubePieces([ductStart(0), [W - 4, 4.4, 84]], 4, P, { maxLength: 60 });
    const b = T.tubePieces([ductStart(4), [4.4, D - 4, 84]], 4, P, { maxLength: 60 });
    return [...a, ...b].sort((p, q) => dep(p.mid) - dep(q.mid)).map((p) => T.tubeSvg(p, { tone: "hi" })).join("");
  }

  // ---- wall instruments (plane y = 0) -------------------------------------------------
  const DIAL_Y = 3.2;
  const dialAt = (cx, cz, r, deg, y = DIAL_Y) => [cx + r * Math.sin((deg * Math.PI) / 180), y, cz + r * Math.cos((deg * Math.PI) / 180)];
  function disc(cx, cz, r, h, style) {
    const F = G.frameOf([cx, 0.2, cz], [0, 1, 0], [1, 0, 0], [0, 0, 1]);
    return S(G.disc(0, h, r, F, P), style);
  }

  const GAUGE = { cx: 250, cz: 134, r: 27 };
  const needle = (deg) => L(poly([dialAt(GAUGE.cx, GAUGE.cz, 0.5, deg), dialAt(GAUGE.cx, GAUGE.cz, GAUGE.r - 5, deg)]), { tone: "hi" });
  function gauge(g) {
    const { cx, cz, r } = GAUGE;
    const out = [disc(cx, cz, r, 3, { tone: "hi" })];
    out.push(L(G.circleOf(G.frameOf([cx, 0.2, cz], [0, 1, 0], [1, 0, 0], [0, 0, 1]), 3, r - 3, P), { tone: "mid" }));
    const minor = [];
    const major = [];
    for (let i = 0; i <= 18; i++) {
      const deg = -135 + (270 * i) / 18;
      (i % 3 === 0 ? major : minor).push(poly([dialAt(cx, cz, r - (i % 3 === 0 ? 8.4 : 6.2), deg), dialAt(cx, cz, r - 4, deg)]));
    }
    out.push(L(minor.join(""), { tone: "lo" }), L(major.join(""), { tone: "mid" }));
    out.push(L(poly([dialAt(cx, cz, r - 9.5, g.baseline), dialAt(cx, cz, r - 3.4, g.baseline)]), { tone: "blue" }));
    out.push(`<g data-part="needle">${needle(g.angle)}</g>`);
    out.push(S(G.disc(3, 5, 2.6, G.frameOf([cx, 0.2, cz], [0, 1, 0], [1, 0, 0], [0, 0, 1]), P), { tone: "hi" }));
    out.push(k.faceTextSvg(k.sideMatrix([cx - 11, DIAL_Y], cz - 12, P, "left"), "STEERING", { size: 3.1, tone: "mid" }));
    const pct = g.share === null ? "--" : `${Math.round(g.share * 100)}%`;
    out.push(k.faceTextSvg(k.sideMatrix([cx - 8, DIAL_Y], cz - 17, P, "left"), pct, { size: 5, tone: "hi" }));
    const hitSvg = hit([[cx - r, 0, cz - r], [cx + r, 0, cz - r], [cx + r, 6, cz + r], [cx - r, 6, cz + r]]);
    return target("steering", "", g.label, out.join(""), hitSvg);
  }

  const CLOCK = { cx: 130, cz: 134, r: 24 };
  function clock(c, nowMs) {
    const { cx, cz, r } = CLOCK;
    const F = G.frameOf([cx, 0.2, cz], [0, 1, 0], [1, 0, 0], [0, 0, 1]);
    const out = [disc(cx, cz, r, 3, { tone: "hi" }), L(G.circleOf(F, 3, r - 2.6, P), { tone: "mid" })];
    const ticks = [];
    for (let i = 0; i < 12; i++) ticks.push(poly([dialAt(cx, cz, r - (i % 3 === 0 ? 7 : 5.2), i * 30), dialAt(cx, cz, r - 3.6, i * 30)]));
    out.push(L(ticks.join(""), { tone: "mid" }));
    const d = new Date(nowMs);
    const mins = d.getMinutes() + d.getSeconds() / 60;
    const hr = ((d.getHours() % 12) + mins / 60) * 30;
    out.push(L(poly([dialAt(cx, cz, 0.5, mins * 6), dialAt(cx, cz, r - 5.5, mins * 6)]), { tone: "hi" }));
    out.push(L(poly([dialAt(cx, cz, 0.5, hr), dialAt(cx, cz, r - 10, hr)]), { tone: "hi" }));
    if (c.jobAngle !== null) out.push(L(poly([dialAt(cx, cz, r - 1.8, c.jobAngle), dialAt(cx, cz, r + 0.2, c.jobAngle)]), { tone: "blue" }), `<circle class="of-job" cx="${iso(dialAt(cx, cz, r + 3.4, c.jobAngle))[0].toFixed(1)}" cy="${iso(dialAt(cx, cz, r + 3.4, c.jobAngle))[1].toFixed(1)}" r="1.5"/>`);
    out.push(S(G.disc(3, 4.6, 2, F, P), { tone: "hi" }));
    out.push(k.faceTextSvg(k.sideMatrix([cx - 9, DIAL_Y], cz - 12, P, "left"), c.nextJob ? clip(`next ${c.nextJob}`, 14) : "no job", { size: 2.8, tone: "mid" }));
    const hitSvg = hit([[cx - r, 0, cz - r], [cx + r, 0, cz - r], [cx + r, 6, cz + r], [cx - r, 6, cz + r]]);
    return target("jobs", "", c.label, out.join(""), hitSvg);
  }

  const FUSE = { x: 318, w: 112, z0: 104, z1: 168 };
  const MODE_Z = { enforce: 8.6, inject: 5.8, advise: 3, off: 0.2 };
  function fuses(f) {
    const out = [slab({ x: FUSE.x, y: 0.2, w: FUSE.w, d: 6, r: 1.5 }, FUSE.z0, FUSE.z1 - FUSE.z0, { tone: "hi" }, 3, 0.4)];
    out.push(L(k.planOutline({ x: FUSE.x + 3, y: 6.2, w: FUSE.w - 6, d: 0.01, r: 0 }, FUSE.z1, P, 2), { tone: "faint" }));
    out.push(L(rect3(FUSE.x + 4, FUSE.x + FUSE.w - 4, FUSE.z0 + 4, FUSE.z1 - 4, 6.3), { tone: "mid" }));
    // main lever
    out.push(L(rect3(FUSE.x + 8, FUSE.x + 16, FUSE.z0 + 10, FUSE.z1 - 10, 6.3), { tone: "mid" }));
    out.push(slab({ x: FUSE.x + 7, y: 6.3, w: 10, d: 3.2, r: 0.8 }, f.main ? FUSE.z1 - 28 : FUSE.z0 + 12, 12, { tone: f.main ? "hi" : "red" }, 2));
    out.push(k.faceTextSvg(k.sideMatrix([FUSE.x + 6, 6.3], FUSE.z1 - 6, P, "left"), f.main ? "MAIN ON" : "MAIN OFF", { size: 2.6, tone: f.main ? "mid" : "red" }));
    f.breakers.forEach((b, i) => {
      const col = i % 6;
      const row = Math.floor(i / 6);
      const bx = FUSE.x + 26 + col * 14;
      const bz = FUSE.z1 - 20 - row * 28;
      out.push(L(rect3(bx - 1, bx + 7, bz - 1, bz + 15, 6.3), { tone: "faint" }));
      out.push(slab({ x: bx, y: 6.3, w: 6, d: 2.6, r: 0.6 }, bz + MODE_Z[b.mode] - 0.2, 4.4, { tone: b.mode === "off" ? "lo" : "hi" }, 2));
    });
    const hitSvg = boxHit({ x: FUSE.x, y: 0, w: FUSE.w, d: 10 }, FUSE.z0, FUSE.z1);
    return target("rules", "", f.label, out.join(""), hitSvg);
  }

  // ---- cabinet --------------------------------------------------------------------------
  const CAB = { x: 150, y: 168, w: 64, d: 46, r: 2 };
  const CAB_FRONT = CAB.y + CAB.d;
  const DRAWER_Z = (slot) => 8 + (7 - slot) * 10.2;
  function cabinet(drawers, offs, overflow) {
    const out = [slab(k.insetPlan(CAB, 2), 0, 4, { tone: "hi" }, 2), slab(CAB, 4, 86, { tone: "hi" }, 3, 0.4), slab(k.insetPlan(CAB, -1.4), 90, 4, { tone: "hi" }, 3, 0.4)];
    if (overflow > 0) out.push(k.faceTextSvg(k.topMatrix([CAB.x + 4, CAB.y + 10], 94, P), `+${overflow}`, { size: 9, tone: "hi" }));
    for (let slot = 7; slot >= 0; slot--) {
      const dr = drawers[slot];
      const z0 = DRAWER_Z(slot);
      const off = offs[slot] || 0;
      const yf = CAB_FRONT + off;
      let svg = "";
      if (off > 0.4) {
        const box = { x: CAB.x + 4, y: CAB_FRONT + 1.2, w: 56, d: off, r: 0.6 };
        svg += slab(box, z0 + 0.6, 6.4, { tone: "mid" }, 2);
        const folders = [];
        for (let i = 0; i < 6; i++) folders.push(k.lineOnTop([box.x + 6 + i * 8.6, box.y + 1.2], [box.x + 6 + i * 8.6, box.y + Math.max(1.4, off - 1.4)], z0 + 7, P));
        svg += L(folders.join(""), { tone: "lo" });
      }
      const fplan = { x: CAB.x + 4, y: yf, w: 56, d: 2.4, r: 0.8 };
      const lit = !!dr?.lit;
      svg += slab(fplan, z0, 9, { tone: dr ? "hi" : "lo", lit }, 2, 0.2);
      if (dr) {
        const yy = yf + 2.5;
        svg += L(seg([CAB.x + 26, yy, z0 + 3.2], [CAB.x + 38, yy, z0 + 3.2]), { tone: "mid" });
        svg += k.faceTextSvg(k.sideMatrix([CAB.x + 7, yy], z0 + 7.6, P, "left"), clip(dr.branch, 9), { size: 2.4, tone: "hi" });
        if (dr.conflict) svg += slab({ x: CAB.x + 46, y: yf, w: 10, d: 1.4, r: 0.3 }, z0 + 9, 3.2, { tone: "red" }, 2);
        if (dr.behind) svg += L(seg([CAB.x + 8, yy, z0 + 1.2], [CAB.x + 56, yy, z0 + 1.2]), { tone: "blue", dashed: true });
        const hp = [[CAB.x + 4, yf, z0], [CAB.x + 60, yf, z0], [CAB.x + 60, yf + 3, z0 + 9], [CAB.x + 4, yf + 3, z0 + 9]];
        if (off > 0.4) hp.push([CAB.x + 4, CAB_FRONT, z0], [CAB.x + 60, CAB_FRONT, z0]);
        out.push(target("worktree", dr.id, dr.label, svg, hit(hp.map((p) => [p[0] - 1, p[1] + 0.5, p[2] - 0.8]))));
      } else {
        svg += L(seg([CAB.x + 26, yf + 2.5, z0 + 3.2], [CAB.x + 38, yf + 2.5, z0 + 3.2]), { tone: "faint" });
        out.push(svg);
      }
    }
    return out.join("");
  }

  // ---- ticker ---------------------------------------------------------------------------
  const TK = { x: 326, y: 196, w: 56, d: 32, r: 2 };
  const TAPE_Y = 221;
  function tape(tk, phase) {
    const pitch = 5;
    const shift = (((phase % pitch) + pitch) % pitch);
    const ticks = [];
    const reds = [];
    const lane = (x0, x1, z, from) => {
      for (let x = x0 + shift; x < x1 - 1; x += pitch) {
        const idx = Math.round((x - from) / pitch);
        const isDeny = tk.denyMarks > 0 && idx % Math.max(3, 13 - tk.denyMarks) === 0 && idx > 0;
        (isDeny ? reds : ticks).push(k.lineOnTop([x, TAPE_Y + (isDeny ? 0.8 : 2)], [x, TAPE_Y + (isDeny ? 6.2 : 5)], z, P));
      }
    };
    lane(328, 383, 29.8, 328);
    lane(386.4, 440, 0.6, 386.4);
    return L(ticks.join(""), { tone: "hi" }) + L(reds.join(""), { tone: "red" });
  }
  function ticker(tk, phase) {
    const out = [slab(TK, 0, 26, { tone: "hi" }, 3, 0.4), slab(k.insetPlan(TK, -2.5), 26, 3, { tone: "hi" }, 3, 0.3)];
    out.push(cyl(338, 210, 8.6, 29, 6, { tone: "hi" }, 22), cyl(370, 210, 8.6, 29, 6, { tone: "hi" }, 22));
    out.push(L(k.ring(338, 210, 5.2, 35, P, 20) + k.ring(370, 210, 5.2, 35, P, 20), { tone: "mid" }));
    out.push(slab({ x: 328, y: TAPE_Y, w: 56, d: 7, r: 0 }, 29, 0.8, { tone: "mid" }, 2));
    out.push(slab({ x: 384, y: TAPE_Y, w: 1.4, d: 7, r: 0 }, 0, 29.8, { tone: "mid" }, 2));
    out.push(slab({ x: 385.4, y: TAPE_Y, w: 56, d: 7, r: 0 }, 0, 0.6, { tone: "mid" }, 2));
    out.push(`<g data-part="tape">${tape(tk, phase)}</g>`);
    out.push(L(seg([328, TAPE_Y, 29.8], [328, TAPE_Y + 7, 29.8]), { tone: "faint" }));
    out.push(k.faceTextSvg(k.sideMatrix([TK.x + 5, TK.y + TK.d], 19, P, "left"), "TICKER", { size: 4, tone: "hi" }));
    out.push(k.faceTextSvg(k.sideMatrix([TK.x + 5, TK.y + TK.d], 12, P, "left"), `${Math.round(tk.rate)}/min`, { size: 3, tone: "mid" }));
    const lamps = [iso([TK.x + 40, TK.y + TK.d, 17]), iso([TK.x + 46, TK.y + TK.d, 17]), iso([TK.x + 52, TK.y + TK.d, 17])];
    out.push(k.dotsSvg(lamps, { size: 1, tone: tk.speed > 0.02 ? "hi" : "faint" }));
    const hitSvg = boxHit({ x: TK.x - 2, y: TK.y - 2, w: TK.w + 4, d: TK.d + 4 }, 0, 36);
    return target("journal", "", tk.label, out.join(""), hitSvg);
  }

  // ---- stamp ----------------------------------------------------------------------------
  const ST = { x: 232, y: 252, w: 60, d: 36, r: 2 };
  const stampHead = (lift) => {
    const z = 24 + lift;
    return slab({ x: ST.x + 11, y: ST.y + 20, w: 10, d: 6, r: 1 }, z, 4, { tone: "hi" }, 2) + cyl(ST.x + 16, ST.y + 23, 2.2, z + 4, 9, { tone: "hi" }, 14) + cyl(ST.x + 16, ST.y + 23, 3.6, z + 13, 3, { tone: "hi" }, 16);
  };
  function stamp(sp, lift) {
    const out = [slab({ x: ST.x + 3, y: ST.y + 2, w: 4, d: ST.d - 4, r: 0.5 }, 0, 18, { tone: "mid" }, 2), slab({ x: ST.x + ST.w - 7, y: ST.y + 2, w: 4, d: ST.d - 4, r: 0.5 }, 0, 18, { tone: "mid" }, 2)];
    out.push(slab(ST, 18, 4, { tone: "mid" }, 3, 0.3));
    out.push(slab({ x: ST.x + 34, y: ST.y + 5, w: 20, d: 26, r: 0 }, 22, 0.7, { tone: "mid" }, 2));
    out.push(L(k.lineOnTop([ST.x + 37, ST.y + 24], [ST.x + 51, ST.y + 24], 22.7, P) + k.lineOnTop([ST.x + 37, ST.y + 27], [ST.x + 48, ST.y + 27], 22.7, P), { tone: "faint" }));
    if (sp.pressed) out.push(L(k.ring(ST.x + 44, ST.y + 14, 4.4, 22.7, P, 16) + k.lineOnTop([ST.x + 41.6, ST.y + 14], [ST.x + 43.4, ST.y + 15.8], 22.7, P) + k.lineOnTop([ST.x + 43.4, ST.y + 15.8], [ST.x + 47, ST.y + 11.6], 22.7, P), { tone: "green" }));
    out.push(slab({ x: ST.x + 6, y: ST.y + 16, w: 20, d: 14, r: 1.5 }, 22, 2, { tone: "hi" }, 3));
    out.push(L(k.planOutline({ x: ST.x + 9, y: ST.y + 19, w: 14, d: 8, r: 1 }, 24, P, 2), { tone: "faint" }));
    out.push(`<g data-part="stamp-head">${stampHead(lift)}</g>`);
    out.push(k.faceTextSvg(k.sideMatrix([ST.x + 5, ST.y + ST.d], 20.4, P, "left"), `GRANTS ${sp.issued} · ${sp.pending} open`, { size: 2.7, tone: "mid" }));
    const hitSvg = boxHit(ST, 0, 40);
    return target("grants", "", sp.label, out.join(""), hitSvg);
  }

  // ---- bell -----------------------------------------------------------------------------
  const BELL = [150, 318];
  const bellSwing = (a) => {
    const F = G.frameOf([BELL[0], BELL[1], 40], [Math.sin(a), 0, -Math.cos(a)], [Math.cos(a), 0, Math.sin(a)], [0, 1, 0]);
    return S(G.solidOf([[0, 1.2], [2.4, 6, 1], [7.4, 9.4, 1], [10.4, 10.8]], F, P), { tone: "hi" }) + S(G.sphereOf([BELL[0] + Math.sin(a) * 12, BELL[1], 40 - Math.cos(a) * 12], 2, P), { tone: "hi" });
  };
  function bell(on, swing) {
    const out = [cyl(BELL[0], BELL[1], 9, 0, 2, { tone: "hi" }, 22), cyl(BELL[0], BELL[1], 1.7, 2, 24, { tone: "hi" }, 12)];
    out.push(`<g data-part="bell-swing">${bellSwing(swing)}</g>`);
    if (on) {
      const arcs = [];
      for (const r of [15, 19]) arcs.push(poly([[BELL[0] - r, BELL[1], 44], [BELL[0] - r - 2, BELL[1], 47]]), poly([[BELL[0] + r, BELL[1], 44], [BELL[0] + r + 2, BELL[1], 47]]));
      out.push(L(arcs.join(""), { tone: "hi" }));
    }
    const label = on ? "Bell: ringing" : "Bell: quiet";
    return target("inbox", "", label, out.join(""), boxHit({ x: BELL[0] - 11, y: BELL[1] - 11, w: 22, d: 22 }, 0, 52));
  }

  // ---- rack -----------------------------------------------------------------------------
  const RK = { x: 372, y: 392, w: 76, d: 24, r: 1.5 };
  function rack(rk) {
    const out = [slab(RK, 0, 66, { tone: "hi" }, 3, 0.4), slab(k.insetPlan(RK, -1.6), 66, 3, { tone: "hi" }, 2)];
    const yf = RK.y + RK.d;
    for (let i = 0; i < 12; i++) {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = RK.x + 4 + col * 35;
      const z = 6 + row * 9;
      const slot = rk.slots[i];
      if (!slot) {
        out.push(L(rect3(x, x + 31, z, z + 7, yf), { tone: "faint" }));
        continue;
      }
      const blade = slab({ x, y: yf, w: 31, d: 2.6, r: 0.5 }, z, 7, { tone: "hi" }, 2);
      const led = L(seg([x + 3, yf + 2.7, z + 3.5], [x + 6, yf + 2.7, z + 3.5]), { tone: slot.lit ? "green" : "lo" });
      out.push(target("session", slot.session, slot.label, blade + led, hit([[x - 1, yf, z - 1], [x + 32, yf, z - 1], [x + 32, yf + 3, z + 8], [x - 1, yf + 3, z + 8]])));
    }
    out.push(k.faceTextSvg(k.sideMatrix([RK.x + 6, yf], 76, P, "left"), rk.total > 0 ? `RACK +${rk.total}` : "RACK", { size: 6, tone: rk.total > 0 ? "hi" : "lo" }));
    return out.join("");
  }

  /** Draw order: the room first, then everything by depth. Wall instruments sit on the wall, before any desk. */
  const ITEMS = () => {
    const key = (x, y, z) => dep([x, y, z]);
    const list = [
      { id: "room", key: -1e9 },
      { id: "wall", key: -9e8 },
      { id: "hub", key: -8e8 },
      { id: "ducts", key: -7e8 },
      { id: "capsBack", key: -6.9e8 },
      { id: "gauge", key: -6e8 },
      { id: "clock", key: -5.9e8 },
      { id: "fuses", key: -5.8e8 },
    ];
    for (let s = 0; s < 8; s++) {
      const f = frame(s);
      const kd = dep(f.pt(40, 30, 20));
      list.push({ id: `desk${s}`, key: kd }, { id: `caps${s}`, key: kd + 0.001 });
    }
    list.push({ id: "cabinet", key: key(CAB.x + 32, CAB.y + 23, 20) });
    list.push({ id: "ticker", key: key(TK.x + 28, TK.y + 16, 15) });
    list.push({ id: "stamp", key: key(ST.x + 30, ST.y + 18, 10) });
    list.push({ id: "bell", key: key(BELL[0], BELL[1], 10) });
    list.push({ id: "rack", key: key(RK.x + 38, RK.y + 12, 30) });
    return list.sort((a, b) => a.key - b.key);
  };

  return {
    W, D, VBW, VBH, P, esc, iso, S, frame, capsulePath, desk, room, sign, hub, ducts, gauge, needle, clock, fuses, cabinet, ticker, tape, stamp, stampHead, bell, bellSwing, rack, ITEMS,
    GAUGE, CLOCK, FUSE, CAB, CAB_FRONT, TK, ST, RK, fmtTime, ductStart,
  };
}
