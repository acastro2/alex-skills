#!/usr/bin/env python3
"""Build impact-deck.html from metrics.json, in the Attain Claude-Code deck style.

The mascot is embedded as a base64 data URI so the HTML is fully self-contained
(no assets/ dependency) and opens anywhere. Print CSS lets system Chrome render a
clean one-slide-per-page PDF with `--headless --print-to-pdf`, so there is no
puppeteer/node dependency.

Usage: python build_deck.py [config.json] [out_dir]
Writes: <out>/impact-deck.html
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

CFG_PATH, OUT = config.resolve_paths(sys.argv)
M = json.loads(open(os.path.join(OUT, "metrics.json")).read())
W = M["generated_windows"]
C = M["counts"]

ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "clawd.png")
try:
    MASCOT = "data:image/png;base64," + base64.b64encode(open(ASSET, "rb").read()).decode()
except FileNotFoundError:
    MASCOT = ""  # deck still renders, just without the mascot


def fmt(x):
    return f"{x:.1f}" if x else "0.0"


def ratio(a, b):
    return "n/a" if not b else f"{a/b:.1f}×"


def delta(a, b):
    return "" if not b else f"{(a/b-1)*100:+.0f}%"


def bar_row(label, cohort_v, rest_v, unit, note=""):
    mx = max(cohort_v, rest_v, 0.001)
    return f"""
      <div class="mrow">
        <div class="mlabel">{label}<span class="munit">{unit}</span></div>
        <div class="mbars">
          <div class="mbar"><span class="mtag">Claude cohort</span>
            <div class="track"><div class="fill coral-bg" style="width:{cohort_v/mx*100:.1f}%"></div></div>
            <span class="mval coral">{fmt(cohort_v)}</span></div>
          <div class="mbar"><span class="mtag">Everyone else</span>
            <div class="track"><div class="fill rest-bg" style="width:{rest_v/mx*100:.1f}%"></div></div>
            <span class="mval">{fmt(rest_v)}</span></div>
        </div>
        <div class="mdelta">{ratio(cohort_v, rest_v)}<span class="mdnote">{note}</span></div>
      </div>"""


def ba_row(label, before_v, after_v, unit):
    mx = max(before_v, after_v, 0.001)
    return f"""
      <div class="mrow">
        <div class="mlabel">{label}<span class="munit">{unit}</span></div>
        <div class="mbars">
          <div class="mbar"><span class="mtag">Before ({W['weeks']['before']:.0f} wk)</span>
            <div class="track"><div class="fill rest-bg" style="width:{before_v/mx*100:.1f}%"></div></div>
            <span class="mval">{fmt(before_v)}</span></div>
          <div class="mbar"><span class="mtag">After (~{W['weeks']['after']:.0f} wk)</span>
            <div class="track"><div class="fill coral-bg" style="width:{after_v/mx*100:.1f}%"></div></div>
            <span class="mval coral">{fmt(after_v)}</span></div>
        </div>
        <div class="mdelta">{delta(after_v, before_v)}<span class="mdnote">/eng/wk</span></div>
      </div>"""


snap, ba = M["snapshot"], M["beforeafter"]
gc, gr = snap["github"]["cohort"], snap["github"]["rest"]
ac, ar = snap["ado"]["cohort"], snap["ado"]["rest"]
TAG = f'<div class="tag"><img src="{MASCOT}">Claude Code @ Attain · Impact</div>'

html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Code @ Attain — Early Impact</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');
:root{{--bg:#1a1a18;--panel:#262624;--panel2:#2f2e2b;--line:#3a3936;--coral:#d97757;--coral-bright:#e8956f;--cream:#faf9f5;--muted:#a8a39a;--green:#7fae8e;--sans:'Inter',ui-sans-serif,system-ui,sans-serif;--mono:'JetBrains Mono',ui-monospace,Menlo,monospace;}}
*{{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
html,body{{background:#0e0e0d;color:var(--cream);font-family:var(--sans);-webkit-font-smoothing:antialiased}}
html{{scroll-snap-type:y mandatory;scroll-behavior:smooth}}
.slide{{scroll-snap-align:center}}
.slide{{position:relative;width:1600px;height:900px;margin:0 auto;background:radial-gradient(120% 120% at 80% -10%, #2a2926 0%, var(--bg) 55%);overflow:hidden;display:flex;flex-direction:column;justify-content:center;padding:96px 110px;border-bottom:1px solid #000;}}
.slide::after{{content:"";position:absolute;right:-160px;bottom:-200px;width:760px;height:760px;background:url('{MASCOT}') no-repeat center/contain;opacity:.05;pointer-events:none;}}
.kicker{{font-family:var(--mono);font-size:20px;letter-spacing:.18em;text-transform:uppercase;color:var(--coral);margin-bottom:26px;font-weight:500}}
h1{{font-size:118px;line-height:.96;font-weight:900;letter-spacing:-.03em}}
h2{{font-size:70px;line-height:1.02;font-weight:800;letter-spacing:-.02em}}
.sub{{font-size:34px;color:var(--muted);font-weight:400;line-height:1.4;margin-top:34px;max-width:1150px}}
.coral{{color:var(--coral)}} .cream{{color:var(--cream)}}
.pageno{{position:absolute;bottom:42px;right:56px;font-family:var(--mono);font-size:18px;color:#5f5d57}}
.tag{{position:absolute;top:48px;left:110px;display:flex;align-items:center;gap:14px;font-family:var(--mono);font-size:19px;color:var(--muted)}}
.tag img{{height:32px;width:auto}}
.hero-spark{{width:auto;height:200px;margin:0 auto 30px;filter:drop-shadow(0 16px 40px rgba(0,0,0,.45))}}
.center{{align-items:center;text-align:center}} .center .sub{{margin-left:auto;margin-right:auto}}
.note{{font-size:24px;color:var(--muted);margin-top:26px;line-height:1.5}}
.pill{{display:inline-block;font-family:var(--mono);font-size:22px;background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:12px 24px;color:var(--cream);margin-top:16px}}
.mwrap{{display:flex;flex-direction:column;gap:22px;margin-top:26px}}
.mrow{{display:grid;grid-template-columns:280px 1fr 150px;gap:28px;align-items:center}}
.mlabel{{font-size:26px;font-weight:700;color:var(--cream);line-height:1.15}}
.munit{{display:block;font-family:var(--mono);font-size:15px;color:var(--muted);font-weight:400;letter-spacing:.04em;margin-top:4px}}
.mbars{{display:flex;flex-direction:column;gap:12px}}
.mbar{{display:grid;grid-template-columns:180px 1fr 70px;align-items:center;gap:16px}}
.mtag{{font-family:var(--mono);font-size:16px;color:var(--muted)}}
.track{{height:26px;background:#100f0e;border:1px solid var(--line);border-radius:7px;overflow:hidden}}
.fill{{height:100%;border-radius:6px}}
.coral-bg{{background:linear-gradient(90deg,var(--coral),var(--coral-bright))}}
.rest-bg{{background:linear-gradient(90deg,#5c6b60,var(--green))}}
.mval{{font-family:var(--mono);font-size:22px;font-weight:700;text-align:right}}
.mdelta{{font-family:var(--mono);font-size:38px;font-weight:800;color:var(--coral);text-align:right;line-height:1}}
.mdnote{{display:block;font-size:14px;color:var(--muted);font-weight:400;margin-top:6px}}
.headrow{{display:flex;gap:20px;margin-top:14px}}
.hstat{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:22px 30px;flex:1}}
.hstat .n{{font-size:52px;font-weight:900;color:var(--coral);line-height:1}}
.hstat .l{{font-size:20px;color:var(--muted);margin-top:8px}}
.caveat{{display:flex;gap:16px;font-size:24px;color:var(--muted);padding:14px 0;border-bottom:1px solid var(--line);line-height:1.4}}
.caveat .cx{{color:var(--coral);font-family:var(--mono);font-weight:700;flex:none}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:30px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:30px 32px}}
.card h3{{font-size:30px;font-weight:800;color:var(--coral);margin-bottom:10px;line-height:1.1}}
.card p{{font-size:23px;color:var(--muted);line-height:1.45}}
.cols{{display:grid;grid-template-columns:1fr 1.15fr;gap:56px;align-items:center}}
.big-list{{list-style:none;margin-top:20px}}
.big-list li{{font-size:26px;font-weight:600;padding:14px 0;border-bottom:1px solid var(--line);display:flex;gap:16px}}
.big-list li .x{{color:var(--coral);font-family:var(--mono);font-weight:700;flex:none}}
.term{{background:#100f0e;border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 30px 60px rgba(0,0,0,.5);font-family:var(--mono)}}
.term .bar{{display:flex;gap:10px;padding:16px 20px;background:#1c1b19;border-bottom:1px solid var(--line)}}
.term .bar i{{width:13px;height:13px;border-radius:50%;display:block}}
.term .bar i:nth-child(1){{background:#e06c5a}}.term .bar i:nth-child(2){{background:#e3b341}}.term .bar i:nth-child(3){{background:#7fae8e}}
.term .body{{padding:28px 32px;font-size:24px;line-height:1.65}}
.term .body .p{{color:var(--coral)}} .term .body .c{{color:var(--cream)}} .term .body .d{{color:var(--muted)}}
.cards.two{{grid-template-columns:repeat(2,1fr)}}
.flow{{display:flex;align-items:stretch;gap:0;margin-top:40px}}
.step{{flex:1;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:26px 20px;font-size:24px;font-weight:700;text-align:center;display:flex;flex-direction:column;justify-content:center}}
.step.out{{border-color:var(--coral);color:var(--coral-bright)}}
.stepd{{display:block;font-family:var(--mono);font-size:15px;font-weight:400;color:var(--muted);margin-top:8px;letter-spacing:.02em}}
.step.out .stepd{{color:var(--coral)}}
.arrow{{flex:none;display:flex;align-items:center;color:var(--coral);font-size:34px;font-weight:700;padding:0 16px}}
.lims{{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-top:24px}}
.lim{{background:#211f1d;border:1px solid var(--line);border-left:3px solid var(--coral);border-radius:10px;padding:22px 22px;font-size:20px;color:var(--muted);line-height:1.4}}
.lim b{{color:var(--cream);font-weight:700;display:block;margin-bottom:7px}}
@page{{size:1600px 900px;margin:0}}
@media print{{html{{scroll-snap-type:none}} .slide{{break-after:page;border-bottom:none}}}}
</style></head>
<body>

<section class="slide center">
  <img class="hero-spark" src="{MASCOT}" alt="">
  <div class="kicker">Adoption · early read</div>
  <h1>Does it <span class="coral">move<br>the needle?</span></h1>
  <div class="sub">{C['cohort_size']} people got Claude Code first. Here's how the engineers among them compare to the rest of the org on GitHub &amp; Azure DevOps, and what changed after the {W['beta_start']} kickoff. Early numbers, honestly framed.</div>
  <div class="pageno">01</div>
</section>

<section class="slide">
  {TAG}
  <div class="kicker">How we did it</div>
  <h2 style="font-size:52px;margin-bottom:4px">Two sources, one <span class="coral">fair comparison.</span></h2>
  <div class="flow">
    <div class="step">GitHub + ADO<span class="stepd">PRs · reviews · closed stories</span></div>
    <div class="arrow">&rarr;</div>
    <div class="step">Tag each person<span class="stepd">cohort or rest</span></div>
    <div class="arrow">&rarr;</div>
    <div class="step">Normalize<span class="stepd">per engineer / week</span></div>
    <div class="arrow">&rarr;</div>
    <div class="step out">Compare<span class="stepd">cohort vs rest &middot; before / after</span></div>
  </div>
  <div class="kicker" style="margin-top:52px;color:var(--muted)">Read it honestly</div>
  <div class="lims">
    <div class="lim"><b>Snapshot, not proof</b>Hand-picked group, so a gap is correlation, not cause.</div>
    <div class="lim"><b>Activity, not usage</b>Measures shipped work, not Claude Code use directly.</div>
    <div class="lim"><b>Early signal</b>"After" is ~{W['weeks']['after']:.0f} wks and grows each week.</div>
    <div class="lim"><b>Relative read</b>Some work lives elsewhere; not absolute output.</div>
  </div>
  <div class="pageno">02</div>
</section>

<section class="slide">
  {TAG}
  <div class="kicker">Cohort vs everyone else · last {W['weeks']['snapshot']:.0f} weeks</div>
  <h2 style="font-size:52px;margin-bottom:2px">More PRs, more reviews. <span class="coral">Level on tickets.</span></h2>
  <div class="mwrap">
    {bar_row("Merged PRs authored", gc['authored']['mean'], gr['authored']['mean'], "/eng/wk · mean", "vs rest")}
    {bar_row("PRs reviewed", gc['reviewed']['mean'], gr['reviewed']['mean'], "/eng/wk · mean", "vs rest")}
    {bar_row("Closed user stories", ac['stories']['mean'], ar['stories']['mean'], "/eng/wk · mean", "vs rest")}
  </div>
  <div class="headrow">
    <div class="hstat"><div class="n">{gc['n_active']}/{C['cohort_size']}</div><div class="l">cohort active on GitHub</div></div>
    <div class="hstat"><div class="n">{ac['n_active']}</div><div class="l">cohort active in ADO</div></div>
    <div class="hstat"><div class="n">{gr['n_active']}</div><div class="l">others active on GitHub</div></div>
    <div class="hstat"><div class="n">{ar['n_active']}</div><div class="l">others active in ADO</div></div>
  </div>
  <div class="note" style="margin-top:16px">Medians agree: authored PRs {fmt(gc['authored']['median'])} vs {fmt(gr['authored']['median'])}/eng/wk. The cohort's edge is on GitHub (authoring + review); ADO story throughput is roughly level. Read as "who's most active", not "Claude Code did this".</div>
  <div class="pageno">03</div>
</section>

<section class="slide">
  {TAG}
  <div class="kicker">Cohort, before vs after kickoff · early signal</div>
  <h2 style="font-size:52px;margin-bottom:2px">After {W['beta_start']}: <span class="coral">the shift so far.</span></h2>
  <div class="mwrap">
    {ba_row("Merged PRs authored", ba['before']['github']['authored']['mean'], ba['after']['github']['authored']['mean'], "/eng/wk")}
    {ba_row("PRs reviewed", ba['before']['github']['reviewed']['mean'], ba['after']['github']['reviewed']['mean'], "/eng/wk")}
    {ba_row("Closed user stories", ba['before']['ado']['stories']['mean'], ba['after']['ado']['stories']['mean'], "/eng/wk")}
  </div>
  <div class="note" style="margin-top:18px"><b class="coral">Caveat that matters:</b> a short window is noisy, and beta folks may have used Claude Code before the kickoff, so "before" isn't perfectly clean. Treat direction, not size.</div>
  <div class="pageno">04</div>
</section>

<section class="slide">
  {TAG}
  <div class="kicker">Why it's worth your time</div>
  <h2 style="font-size:52px;margin-bottom:2px">Hand off the <span class="coral">boring 80%.</span></h2>
  <div class="cards">
    <div class="card"><h3>Starting something</h3><p>Describe the change, get a plan and a first draft, then steer. Skip the blank page.</p></div>
    <div class="card"><h3>Before the PR</h3><p>A review pass catches the dumb stuff at your desk, not from your reviewer.</p></div>
    <div class="card"><h3>The tedious stuff</h3><p>Tests, boilerplate, "where is this even defined", changelog entries: the work you keep putting off.</p></div>
  </div>
  <div class="note" style="margin-top:30px;font-size:28px">It's not about typing more. It's handing off the boring 80% so your attention lands on the <b class="cream">hard 20%</b>.</div>
  <div class="pageno">05</div>
</section>

<section class="slide">
  {TAG}
  <div class="kicker">Set it and let it run</div>
  <h2 style="font-size:52px;margin-bottom:6px">Give it a <span class="coral">finish line.</span> <span style="font-family:var(--mono);font-size:32px;color:var(--muted)">/goal</span></h2>
  <div class="cols">
    <div>
      <ul class="big-list">
        <li><span class="x">Set</span> a condition, Claude works turn after turn until it's true</li>
        <li><span class="x">Check</span> a fast model judges "done yet?" from what Claude showed that turn</li>
        <li><span class="x">Bound</span> it, add "or stop after N turns" so it can't run forever</li>
      </ul>
      <div class="note" style="margin-top:18px">You met <b class="cream" style="font-family:var(--mono)">/loop</b> and <b class="cream" style="font-family:var(--mono)">/schedule</b> on Day 2. <span class="coral">/goal</span> is the same reflex, but it stops when the work is <i>done</i>, not on a timer. Needs CLI v2.1.139+.</div>
    </div>
    <div class="term">
      <div class="bar"><i></i><i></i><i></i></div>
      <div class="body">
        <div class="d"># set a finish line, it keeps going until true</div>
        <div><span class="p">&gt; /goal</span> <span class="c">all tests in api/ pass and lint is clean</span></div>
        <div class="d">  &#9678; goal active</div>
        <br>
        <div class="d"># check progress &middot; stop early</div>
        <div><span class="p">&gt; /goal</span><span class="d">          # turns, tokens, last reason</span></div>
        <div><span class="p">&gt; /goal clear</span></div>
        <br>
        <div class="d"># always give it a bound</div>
        <div><span class="p">&gt; /goal</span> <span class="c">...pass, or stop after 20 turns</span><span class="coral">&#9613;</span></div>
      </div>
    </div>
  </div>
  <div class="pageno">06</div>
</section>

<section class="slide">
  {TAG}
  <div class="kicker">Your turn · open floor</div>
  <h2 style="font-size:56px;margin-bottom:6px">What's <span class="coral">getting in the way?</span></h2>
  <div class="note" style="margin-top:0;font-size:26px">Be honest, every blocker here is something we can fix. Which one is you?</div>
  <div class="cards two" style="margin-top:26px">
    <div class="card"><h3>Setup &amp; IDE friction</h3><p>Install, Visual Studio, config, permissions, MCP: something in the way before you even start?</p></div>
    <div class="card"><h3>Not sure what to use it for</h3><p>Which of your actual tasks pay off, and which aren't worth it yet?</p></div>
    <div class="card"><h3>Don't fully trust it</h3><p>On our codebase, on real changes: what would it take to trust the output?</p></div>
    <div class="card"><h3>Habit &amp; workflow</h3><p>Keep forgetting it's there, or it doesn't slot into how you already work?</p></div>
  </div>
  <div class="note" style="margin-top:24px">Anything else, speed, cost, a task it flubbed? Say it. This is how we unblock the next month.</div>
  <div class="pageno">07</div>
</section>

<section class="slide center">
  <img class="hero-spark" src="{MASCOT}" alt="">
  <div class="kicker">What we can and can't say</div>
  <h2 style="font-size:56px">Promising. <span class="coral">Not yet proven.</span></h2>
  <div class="sub" style="max-width:1200px">The cohort is clearly among the most active engineers, on GitHub and in ADO. Whether Claude Code <i>caused</i> a lift needs a clean read over time: a fixed before/after per person, a matched control group, and cycle-time alongside volume. This is the baseline we measure against next week.</div>
  <div class="pill">Re-run weekly · the "after" window grows · add a matched control + cycle time</div>
  <div class="pageno">08</div>
</section>

<script>
const slides=[...document.querySelectorAll('.slide')];let i=0;
function go(n){{i=Math.max(0,Math.min(slides.length-1,n));slides[i].scrollIntoView();}}
addEventListener('keydown',e=>{{
  if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key)){{e.preventDefault();go(i+1);}}
  if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){{e.preventDefault();go(i-1);}}
}});
</script>
</body></html>
"""

open(os.path.join(OUT, "impact-deck.html"), "w").write(html)
print(f"Wrote {OUT}/impact-deck.html")
