---
name: cohort-metrics
description: >-
  Compare a defined cohort of engineers against the rest of the org on GitHub
  (merged PRs authored, PRs reviewed) and Azure DevOps (closed user stories,
  story points), then build a branded Attain "Claude Code impact" HTML deck + PDF.
  Use this whenever the user wants to measure or present engineering-adoption
  impact for a group: comparing beta testers / a pilot group / a tool cohort /
  seat holders vs everyone else, a "who ships more" or before-vs-after read, a
  weekly or recurring engineering-metrics deck, or any GitHub-plus-ADO
  productivity comparison across two groups of people. Trigger it even when the
  user does not say "cohort" or "skill", as long as they want a two-group
  engineering-activity comparison or a recurring adoption-impact deck. For a
  single engineer's report use the performance-report skill instead.
---

# Cohort Metrics

Measures whether a cohort of engineers (e.g. the Claude Code beta seat holders)
differs from the rest of the org in shipping activity, and packages it as a
presentation-ready deck. Built to be **re-run weekly**: all analysis windows are
computed from today at run time, so the only thing you ever edit is the cohort
list when seats change.

## What it produces (in the output dir, default `./cohort-out/`)

- `impact-deck.html` — 5-slide deck (self-contained, Attain Claude-Code style)
- `impact-deck.pdf` — same, one slide per page
- `metrics.json` — group aggregates behind the deck
- `per_person.csv` — **private** per-person numbers. This is individual output
  data: keep it internal, share aggregates not a per-person leaderboard.
- `github_raw.json`, `ado_raw.json` — cached raw pulls (re-aggregate without
  re-hitting the APIs)

## Prerequisites

- `gh` CLI authenticated with read access to the configured orgs
  (`gh auth status` should list the account). `admin:org` or `read:org` scope is
  needed to list org members.
- `AZURE_DEVOPS_PAT` exported, with Work Items (read). Regenerate at the ADO
  org's `_usersSettings/tokens` page. The scripts use it only to authenticate to
  ADO and never print it.
- `python3`. No node/puppeteer needed (PDF uses system Chrome).

## Run it

1. **Config.** First time, copy the template and edit the `cohort` list. The
   template is pre-filled with the Attain orgs, ADO base, and current seat list,
   so a weekly re-run usually needs no edits at all:
   ```bash
   cp <skill>/references/roster.example.json cohort-config.json
   ```
   Fields: `beta_start` (the fixed kickoff date), `snapshot_weeks` /
   `baseline_weeks` (window lengths, default 13), `github_orgs`, `ado_base`,
   `cohort` (name + email + tier), `login_overrides` (email → GitHub login, for
   anyone the resolver misses).

2. **Pull + build**, in order. Each script takes `[config] [out_dir]`,
   defaulting to `cohort-config.json` and `cohort-out/`:
   ```bash
   python3 <skill>/scripts/collect_github.py     # ~4-6 min (paced API calls)
   python3 <skill>/scripts/collect_ado.py        # ~30 s
   python3 <skill>/scripts/aggregate.py          # instant; prints headline numbers
   python3 <skill>/scripts/build_deck.py         # instant
   bash    <skill>/scripts/make_pdf.sh cohort-out
   ```
   `collect_github.py` is the slow step: it pages one search query per org per
   week and pulls reviews for every org member, sleeping ~1.5 s between calls to
   stay under GitHub's 30/min search limit. Let it run in the background.

3. **Open** `cohort-out/impact-deck.html` in a browser (or hand over the PDF).

## Verify before trusting it

The whole comparison rides on **identity resolution**, so check it, don't assume:

- After `collect_github.py`, it logs how each cohort member resolved
  (`email-localpart`, `name-exact`, or `unresolved`). Anyone `unresolved` is
  either a non-engineer or needs a `login_overrides` entry.
- The dangerous failure is a member who resolved to a **wrong** login that looks
  right: high ADO story count but 0 authored PRs. Cross-check per member from the
  raw files, e.g.:
  ```bash
  python3 -c "import json;G=json.load(open('cohort-out/github_raw.json'));A=json.load(open('cohort-out/ado_raw.json'));R=json.load(open('cohort-config.json'))
  for p in R['cohort']:
   lg=G['resolved'].get(p['email']);pr=len(G['authored'].get(lg,{})) if lg else 0;ado=len(A['by_email'].get(p['email'].lower(),[]))
   print(f\"{p['name']:28s} {str(lg):26s} PRs={pr:3d} ADO={ado:3d}\", '<-- CHECK' if ado>=10 and pr==0 else '')"
  ```
  A cohort member you *know* is a heavy coder showing 0 PRs means the login is
  wrong or their repos are outside `github_orgs`. Fix via `login_overrides` or by
  adding the org, then re-run.
- Sanity-check one person whose real numbers you know (often yourself).

## How the numbers are built (and why)

- **Groups are per-system.** GitHub is keyed by resolved login, ADO by assignee
  email (`uniqueName`, an exact match). A person can be cohort in one and absent
  in the other; that's fine, each system is bucketed independently.
- **Rates are per-active-engineer-per-week with per-metric denominators.** The
  authored-PR rate is averaged only over people who authored ≥1 PR; reviews over
  reviewers; stories over people with stories. A reviewer-only or ticket-only
  person is *not* a zero in the authored rate. Counting them as zeros would
  punish role specialisation and understate real throughput. Windows compare
  fairly because everything is normalised to per-week.
- **Reviews are pulled for the whole member universe**, not just PR authors,
  because review-heavy people who rarely author would otherwise be missing from
  the "rest" group and inflate the cohort's review lead.
- **Authored PRs are pulled in weekly chunks** because an org-level
  `gh search prs` truncates at 1000 results. If `aggregate.py` /
  `collect_github.py` reports `truncated_chunks`, a single week exceeded 1000 in
  one org — narrow the chunk (edit `weekly_windows`) or it's an undercount.

## Honesty is the point, keep it

This compares a **hand-picked** cohort to everyone else, so a gap is a snapshot,
not proof Claude Code caused anything (selection bias). The deck says this
out loud on the method slide and labels before/after as an early signal. Don't
strip those caveats to make a cleaner story: a metrics deck that overclaims gets
picked apart, and the honest version is more persuasive to engineers. The `after`
window grows every week you re-run, so the before/after read strengthens on its
own over time. The genuinely strong next step (noted on the final slide) is a
matched control group and cycle-time alongside volume.

## Customising

- **Different windows:** change `snapshot_weeks` / `baseline_weeks` in the config.
- **Different orgs / ADO project:** edit `github_orgs` / `ado_base`.
- **New metric (e.g. cycle time):** PR `createdAt`/`closedAt` are already in
  `github_raw.json`; add the calc in `aggregate.py` and a `bar_row` in
  `build_deck.py`. Keep counts as the lead metric and story points secondary
  (they're frequently blank).
- **Reproducible / dated run:** set `"today": "YYYY-MM-DD"` in the config to pin
  the windows instead of using the real current date.
