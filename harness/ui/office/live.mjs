// The live office. Runs in the page: it draws every item from geometry.mjs, and moves the
// parts that move (tape, stamp, needle, drawers, bell, capsules) from one time-based loop.
// Needs `k`, `G`, `T` (the anatomy kit) and `makeOffice` in scope; build.mjs puts them there.

const MAX_DT = 1 / 30;
const FLIGHT_MS = 2600;
const DRAWER_OUT = 22;
const SHORT = {
  session: "a session desk",
  worktree: "a worktree drawer",
  inbox: "the in-tray",
  journal: "the journal ticker",
  grants: "the grant stamp",
  jobs: "the job clock",
  rules: "the fuse box",
  steering: "the steering gauge",
};

let mounts = 0;

export function mountOffice(el, initial, opts) {
  const uid = ++mounts;
  const O = makeOffice(k, G, T);
  let state = initial;
  let theme = opts.theme === "light" ? "light" : "dark";
  const t0 = performance.now();
  const still = matchMedia("(prefers-reduced-motion: reduce)");

  const items = O.ITEMS();
  const svgBody = items.map((i) => `<g data-item="${i.id}"></g>`).join("");
  el.innerHTML = `<div class="of-root iso" data-theme="${theme}"><figure class="iso-figure of-figure"><div class="iso-plate">
    <div class="iso-plate-corners" aria-hidden="true"><span class="iso-plate-corner" data-corner="fig">Fig. 1</span><span class="iso-plate-corner" data-corner="title">Harness office</span><span class="iso-plate-corner" data-corner="hint">Click a part to open it</span><span class="iso-plate-corner" data-corner="readout" data-readout></span></div>
    <div class="of-stage"><svg class="iso-svg of-svg" viewBox="0 0 ${O.VBW} ${O.VBH}" role="group" aria-label=""><defs></defs>${svgBody}</svg></div>
    <p class="of-sr" role="status" aria-live="polite"></p></div></figure></div>`;
  const root = el.querySelector(".of-root");
  const svg = el.querySelector(".of-svg");
  const readout = el.querySelector("[data-readout]");
  const sr = el.querySelector(".of-sr");
  const slotOf = {};
  for (const g of svg.querySelectorAll("[data-item]")) slotOf[g.dataset.item] = g;

  // ---- animated values ------------------------------------------------------------------
  const anim = {
    phase: 0,
    lift: state.stamp.pressed ? 0 : 9,
    needle: state.gauge.angle,
    drawers: Array(8).fill(0),
    swing: 0,
    bellT: 0,
  };
  const targetDrawer = (s, i) => (s.drawers[i] && s.drawers[i].open && !s.drawers[i].removed ? DRAWER_OUT : 0);
  anim.drawers = anim.drawers.map((_, i) => targetDrawer(state, i));
  const flights = new Map(); // capsule key -> start time (performance.now)
  const noteFlights = (s) => {
    for (const c of s.capsules) if (!flights.has(c.key)) flights.set(c.key, performance.now() - c.age);
  };
  noteFlights(state);

  // ---- swap an item, keeping keyboard focus where it was ---------------------------------
  const sigs = {};
  function swap(node, html) {
    const had = node.contains(document.activeElement) ? document.activeElement : null;
    const kind = had && had.dataset ? had.dataset.kind : null;
    const id = had && had.dataset ? had.dataset.id : null;
    const slot = had && had.dataset ? had.dataset.slot : null;
    node.innerHTML = html;
    if (kind) {
      const pick = [...node.querySelectorAll(".of-target")].find((t) => t.dataset.kind === kind && (t.dataset.id || "") === (id || "") && (t.dataset.slot || "") === (slot || ""));
      if (pick) pick.focus({ preventScroll: true });
    }
  }
  function draw(id, sig, html) {
    if (sigs[id] === sig) return;
    sigs[id] = sig;
    swap(slotOf[id], typeof html === "function" ? html() : html);
  }

  // ---- capsules ---------------------------------------------------------------------------
  const pathCache = {};
  function route(slot, side) {
    const key = `${slot}:${side ? 1 : 0}`;
    if (pathCache[key]) return pathCache[key];
    const pts = O.capsulePath(slot, side);
    const cum = [0];
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + G.len3(G.sub3(pts[i], pts[i - 1])));
    return (pathCache[key] = { pts, cum });
  }
  function along(r, t) {
    const total = r.cum[r.cum.length - 1];
    const d = Math.min(total, Math.max(0, t) * total);
    let i = 1;
    while (i < r.cum.length - 1 && r.cum[i] < d) i++;
    const seg = r.cum[i] - r.cum[i - 1] || 1;
    const u = (d - r.cum[i - 1]) / seg;
    return { p: G.lerp3(r.pts[i - 1], r.pts[i], u), dir: G.unit3(G.sub3(r.pts[i], r.pts[i - 1])) };
  }
  function capsuleSvg(c, now) {
    const t = (now - flights.get(c.key)) / FLIGHT_MS;
    if (t < 0 || t > 1) return null;
    const e = t * t * (3 - 2 * t);
    const { p, dir } = along(route(c.slot, c.side), e);
    const F = G.frameAlong(p, dir);
    return { back: p[2] >= 80, svg: k.solidSvg(G.disc(-4.2, 4.2, 2.1, F, O.P), { tone: "hi", lit: true }) + k.solidSvg(G.sphereOf(G.add3(p, G.mul3(dir, 4.2)), 2.1, O.P), { tone: "hi", lit: true }) };
  }
  function drawCapsules(now) {
    const back = [];
    const bySlot = Array.from({ length: 8 }, () => []);
    for (const c of state.capsules) {
      const r = capsuleSvg(c, now);
      if (!r) continue;
      (r.back ? back : bySlot[c.slot]).push(r.svg);
    }
    draw("capsBack", back.length ? `b${Math.round(now / 33)}` : "none", back.join(""));
    bySlot.forEach((list, s) => draw(`caps${s}`, list.length ? `c${Math.round(now / 33)}` : "none", list.join("")));
  }

  // ---- drawing from state -----------------------------------------------------------------
  const clockMs = (now) => state.now + (now - t0);
  const minuteOf = (now) => Math.floor(clockMs(now) / 60000);
  const flightsLive = (now) => state.capsules.some((c) => flights.has(c.key) && now - flights.get(c.key) < FLIGHT_MS + 50);
  const anyRunning = () => state.desks.some((d) => d && d.lamp) || state.sides.some((d) => d && d.lamp);

  function drawAll(now) {
    svg.setAttribute("aria-label", state.summary);
    draw("room", "static", () => O.room());
    draw("wall", state.host, () => O.sign(state.host));
    draw("hub", `${anyRunning() ? 1 : 0}${state.capsules.length ? 1 : 0}`, () => O.hub(anyRunning() || state.capsules.length > 0));
    draw("ducts", "static", () => O.ducts());
    draw("gauge", JSON.stringify([state.gauge.share, state.gauge.label]), () => O.gauge({ ...state.gauge, angle: anim.needle }));
    draw("clock", JSON.stringify(state.clock) + minuteOf(now), () => O.clock(state.clock, clockMs(now)));
    draw("fuses", JSON.stringify(state.fuses), () => O.fuses(state.fuses));
    for (let i = 0; i < 8; i++) {
      draw(`desk${i}`, JSON.stringify([state.desks[i], state.sides[i], state.empty && i === 0]), () => O.desk(i, state.desks[i], state.sides[i], uid, { empty: state.empty && i === 0 }));
    }
    draw("ticker", JSON.stringify(state.ticker), () => O.ticker(state.ticker, anim.phase));
    draw("stamp", JSON.stringify(state.stamp), () => O.stamp(state.stamp, anim.lift));
    draw("bell", JSON.stringify([state.bell]), () => O.bell(state.bell, anim.swing));
    draw("rack", JSON.stringify(state.rack), () => O.rack(state.rack));
    drawCabinet();
    drawCapsules(now);
    const shown = tourLabel || state.readout;
    if (readout.textContent !== shown) readout.textContent = shown;
    if (sr.textContent !== state.summary) sr.textContent = state.summary;
  }
  function drawCabinet() {
    const offs = anim.drawers.map((v) => Math.round(v * 2) / 2);
    draw("cabinet", JSON.stringify([state.drawers, state.drawerOverflow, offs]), () => O.cabinet(state.drawers, offs, state.drawerOverflow));
  }

  // ---- the loop ---------------------------------------------------------------------------
  let raf = 0;
  let last = 0;
  let visible = true;
  const ease = (cur, target, dt, tau) => cur + (target - cur) * (1 - Math.exp(-dt / tau));
  const settle = (cur, target, eps) => (Math.abs(target - cur) < eps ? target : cur);

  function step(dt, now) {
    let moving = false;
    const tapeSpeed = state.ticker.speed * 46;
    if (tapeSpeed > 0.01 && !still.matches) {
      anim.phase = (anim.phase + tapeSpeed * dt) % 5;
      slotOf.ticker.querySelector('[data-part="tape"]').innerHTML = O.tape(state.ticker, anim.phase);
      moving = true;
    }
    const liftTo = state.stamp.pressed ? 0 : 9;
    if (anim.lift !== liftTo) {
      anim.lift = settle(ease(anim.lift, liftTo, dt, 0.16), liftTo, 0.05);
      slotOf.stamp.querySelector('[data-part="stamp-head"]').innerHTML = O.stampHead(anim.lift);
      moving = true;
    }
    if (anim.needle !== state.gauge.angle) {
      anim.needle = settle(ease(anim.needle, state.gauge.angle, dt, 0.35), state.gauge.angle, 0.05);
      slotOf.gauge.querySelector('[data-part="needle"]').innerHTML = O.needle(anim.needle);
      moving = true;
    }
    let drawerMoving = false;
    anim.drawers = anim.drawers.map((v, i) => {
      const t = targetDrawer(state, i);
      if (v === t) return v;
      drawerMoving = true;
      return settle(ease(v, t, dt, 0.22), t, 0.1);
    });
    if (drawerMoving) {
      drawCabinet();
      moving = true;
    }
    const swingTo = state.bell && !still.matches ? 0.5 * Math.sin((anim.bellT += dt) * 7.5) : 0;
    if (state.bell || anim.swing !== 0) {
      anim.swing = state.bell ? swingTo : settle(ease(anim.swing, 0, dt, 0.25), 0, 0.01);
      slotOf.bell.querySelector('[data-part="bell-swing"]').innerHTML = O.bellSwing(anim.swing);
      moving = true;
    }
    if (flightsLive(now)) {
      drawCapsules(now);
      moving = true;
    } else if (flights.size) {
      drawCapsules(now);
      for (const [key, t] of flights) if (now - t > FLIGHT_MS + 50) flights.delete(key);
    }
    if (minuteOf(now) !== sigsMinute) {
      sigsMinute = minuteOf(now);
      drawAll(now);
    }
    return moving;
  }
  let sigsMinute = minuteOf(performance.now());

  function frame(now) {
    raf = 0;
    const dt = Math.min(MAX_DT, Math.max(0, (now - last) / 1000));
    last = now;
    if (step(dt, now)) schedule();
  }
  function schedule() {
    if (raf || destroyed || !visible || document.hidden || still.matches) return;
    last = performance.now();
    raf = requestAnimationFrame(frame);
  }
  function halt() {
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
  }
  // Reduced motion: snap everything to its target, once, and stay still.
  function snap() {
    anim.lift = state.stamp.pressed ? 0 : 9;
    anim.needle = state.gauge.angle;
    anim.drawers = anim.drawers.map((_, i) => targetDrawer(state, i));
    anim.swing = 0;
    flights.clear();
    for (const key of Object.keys(sigs)) delete sigs[key];
    drawAll(performance.now());
  }

  // ---- idle tour: when nothing changes, the figure points at each part in turn ------------------
  let tourLabel = "";
  let tourNode = null;
  let tourTimer = 0;
  let tourIndex = 0;
  let quiet = performance.now();
  const endTour = () => {
    if (tourNode) tourNode.removeAttribute("data-tour");
    tourNode = null;
    if (tourLabel) {
      tourLabel = "";
      readout.textContent = state.readout;
    }
  };
  function tour() {
    tourTimer = setTimeout(tour, 3200);
    if (destroyed || still.matches || document.hidden || !visible) return;
    if (performance.now() - quiet < 9000) return;
    endTour();
    const nodes = [...svg.querySelectorAll(".of-target")];
    if (!nodes.length) return;
    tourNode = nodes[tourIndex++ % nodes.length];
    tourNode.setAttribute("data-tour", "");
    tourLabel = (tourNode.getAttribute("aria-label") || SHORT[tourNode.dataset.kind] || "").split(":")[0].toLowerCase();
    readout.textContent = tourLabel;
  }
  const wake = () => {
    quiet = performance.now();
    endTour();
  };

  // ---- input ------------------------------------------------------------------------------
  function select(node) {
    const kind = node.dataset.kind;
    const id = node.dataset.id;
    opts.onSelect(id ? { kind, id } : { kind });
  }
  const onClick = (e) => {
    const node = e.target.closest(".of-target");
    if (node && svg.contains(node)) select(node);
  };
  const onKey = (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const node = e.target.closest && e.target.closest(".of-target");
    if (!node || !svg.contains(node)) return;
    e.preventDefault();
    select(node);
  };
  svg.addEventListener("click", onClick);
  svg.addEventListener("keydown", onKey);
  for (const ev of ["pointermove", "keydown", "focusin"]) root.addEventListener(ev, wake);

  let destroyed = false;
  const onVis = () => (document.hidden ? halt() : schedule());
  const onMotion = () => (still.matches ? (halt(), snap()) : (drawAll(performance.now()), schedule()));
  document.addEventListener("visibilitychange", onVis);
  still.addEventListener("change", onMotion);
  const io = new IntersectionObserver(
    (entries) => {
      visible = entries[entries.length - 1].isIntersecting;
      if (visible) schedule();
      else halt();
    },
    { rootMargin: "120px" },
  );
  io.observe(root);

  drawAll(performance.now());
  if (still.matches) snap();
  schedule();
  tourTimer = setTimeout(tour, 3200);

  return {
    update(next) {
      const before = state;
      state = next;
      noteFlights(next);
      wake();
      drawAll(performance.now());
      if (still.matches) snap();
      else if (before !== next) schedule();
    },
    setTheme(t) {
      theme = t === "light" ? "light" : "dark";
      root.dataset.theme = theme;
    },
    destroy() {
      destroyed = true;
      halt();
      clearTimeout(tourTimer);
      io.disconnect();
      document.removeEventListener("visibilitychange", onVis);
      still.removeEventListener("change", onMotion);
      svg.removeEventListener("click", onClick);
      svg.removeEventListener("keydown", onKey);
      el.innerHTML = "";
    },
  };
}
