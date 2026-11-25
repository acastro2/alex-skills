# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Plain TypeScript and HTML, no framework. Served by `harness serve` (Bun) on 127.0.0.1, with live updates from the ledger over server-sent events. The office figure uses the anatomy kit (`iso-kit.ts`). Confirmed by Alex, 2026-11-25.

## Users

One user: Alex, an enterprise architect who runs many AI coding sessions a day in OpenCode and Claude Code, on a Mac and a Linux VM. He opens this page in Edge on the Mac to see what every session is doing, and to act on what needs him, without visiting each terminal tab.

## Product Purpose

The harness UI shows the live state of the harness on one host: sessions and workers, waiting questions, worktrees and conflicts, proof bundles, rules and send-backs, the journal, harness changes and jobs. It lets Alex answer a waiting question, mark a wrong send-back, grant a merge or a harness change, and switch the harness off or on. Success: Alex knows what needs him in one glance, and stops typing steering prompts such as "merged", "link?" and "what now?" (28% of his prompts in the measured week).

## Positioning

Every number and moving part on the page comes from the harness's own ledger and journal, not from an agent's report. It shows what the harness proved, not what an agent claimed.

## Operating Context

- One page per host; the VM page reaches the Mac browser through local port forwarding.
- Many sessions run in parallel, each in its own git worktree.
- Alex works async and switches context often; the page is a glance-then-act tool, kept open beside the terminals.
- Actions that change state need a passkey tap (Touch ID on the Mac). A 30-minute session covers read views, `harness wrong` and question answers.

## Capabilities and Constraints

- Source of truth: `~/.local/state/harness/ledger.db` (schema in `docs/specs/harness-ledger.erd.json`). The page reads it only through the harness modules.
- First view is an isometric office floor (anatomy figure, Hero size). Up to 8 desks; more sessions go on a "+N" rack. Workers sit at a smaller desk beside their parent.
- Eight working views: Inbox, Sessions and workers, Worktrees and conflicts, Proof bundles, Rules, Journal and replay, Harness changes, Jobs.
- Agents must never be able to act on the page: the guard denies agent shell calls to its port and `browse` access to it (D61).
- Local only: no phone access (O9 in `docs/specs/harness-office.md`).

## Brand Commitments

None beyond the anatomy figure style (isometric, solid parts, one lit accent) and the decision that the office has no human figures.

## Evidence on Hand

- The harness spec: `docs/specs/harness-evolution.md`.
- The ledger schema: `docs/specs/harness-ledger.erd.json`.
- Steering counts from 2026-11-19 to 2026-11-25 (in the spec's Why section).
- No production data yet: the harness is not built.

## Product Principles

1. Truth over story: show what the ledger recorded, never an agent's summary as fact.
2. What needs Alex comes first: waiting questions, stuck sessions and conflicts are the loudest things on the page.
3. One glance, then one click: the office answers "is anything wrong?"; a working view answers "what exactly?".
4. Fun that carries data: every playful part of the office is a true signal, or it is removed.

## Accessibility & Inclusion

Keyboard reachable, and every office signal also exists as text in a working view. Reduced motion stops the figure. Both light and dark themes.
