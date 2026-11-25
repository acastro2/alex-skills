---
version: 1
slug: "ui-app-index-html"
primary_target: "ui/app/index.html"
related_targets: []
---

# Surface brief: harness working views

Scope: Operate. The dashboard (home), the 8 working views behind it, the top bar and the left rail of `harness serve`.

Audience and job: Alex, beside his terminals. He opens the page to see what needs him, acts in seconds (answer, wrong, apply, off), and leaves. Frequency: many glances a day, a few actions. Constraints: built for 2560x1440 (27 inch) and 3840x2160 at 1.5x (32 inch), where the home page does not scroll; 1920 and 1440 degrade to fewer columns; 390 stacks; local only, keyboard reachable, light and dark. Answers to the new-work interview came from `docs/specs/harness-office.md` (O1 to O14) and from Alex's brief for the dashboard ("I want to see as much as I can, and data and processes following"), not from a live interview: this run had no way to ask.

Decision: code-led (Operate is always code-led; `.impeccable/config.json` agrees). Established world: O12 fixes it as the anatomy paper and ink palette, one lit accent, the anatomy type.

## Direction contract

THESIS: The working views are the plain back room of the office figure: a dense tool screen that reads like an engineer's drawing sheet, not a SaaS dashboard. It refuses the card grid with a hero number; every view is a ruled table or list with one amber mark for what needs Alex.

OWN-WORLD: Paper and ink. Light: page #f2f2ef, plate #fbfbfa, ink #18181a. Dark: page #0b0b0b, plate #131313, ink #e6e6e6. Greys carry structure. Hairline 1px rules, square 2px corners, no shadows. One lit accent: amber, used only for "needs Alex" (waiting question, stuck, the selected item). Red and green only mark verdicts and conflicts. One system sans for labels and prose, the anatomy mono for ids, SHAs, times and numbers. The office figure carries its own plate corners and mono captions, as the anatomy card does.

STORY: Alex sees the badge count on the rail, opens Inbox, reads the question and its options, taps one. Or he sees a red conflict, reads why in Worktrees, and knows the waker owns it. He never opens a terminal tab to learn state.

FIRST VIEWPORT: Top bar (host, harness on/off, session timer, notify, theme as three buttons). Left rail 224px: Dashboard, then 8 views with count badges; amber badge when the count needs Alex. Main area opens on the dashboard: needs you at top left, live sessions and processes beside it, the journal tail following in the third column, the office figure (its own frame) with worktrees and proof bundles on the right. At 390 the rail becomes a scrolling tab strip and the panels stack.

FORM: Operate shell: top bar plus side nav, ruled tables, inline expansion, no modals. Seed: none (pinned) "Operate surfaces are code-led" and O12.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
