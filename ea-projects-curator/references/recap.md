# Forum recap

Read this for recap drafting and review, including weekly page assembly. Board-only tasks do not
need it. Shared source lookup and missing-note handling stay in
[SKILL.md, Forum recap](../SKILL.md#forum-recap--generate-it-from-the-scribe-transcript-note).
Alex's pasted notes still win verbatim; the prompt below is for generated recaps.

Apply the [shared exclusion screen and review gate](../SKILL.md). Assemble the page using
[Weekly newsletter](../SKILL.md#weekly-newsletter--architecture-weekly); this reference does not
change the weekly run order or who approves list writes and publishes the page.

## Contents

- Teams garbles proper nouns
- The recap prompt (Alex's wording)
- Recap gates
- Verify the draft against the note
- Then run `docs-reviewer`

## Teams garbles proper nouns — verify or omit, never publish a guess

`scribe` applies the glossary at `<vault>/Scribe/Glossary.md` (Lucidchart, FireMon, Ivanti, ADO,
CURO, Five9, SE), so most noise is gone. Verify every remaining proper noun: correct only what you
can confirm, otherwise describe the thing without naming it. A confirmed new garble is appended to
that glossary as `- wrong => Right`; it is the one scribe-owned file the curator may append to. If
the note ends mid-sentence, say so in the recap footer rather than inventing an ending.

## The recap prompt (Alex's wording — use it as-is)

> Create a shareable post-meeting recap for the Architecture Review Forum. Be concise and factual —
> pull only from what was actually said. Use this exact structure and these headings:
>
> **Architecture Review Forum — [Meeting Date]**
> Put the actual meeting date on this header line.
>
> **Objective** — 1-2 sentences: what this session set out to accomplish.
>
> **Outcome** — one line stating whether the objective was met: [Achieved] / [Partially achieved] /
> [Not achieved], followed by a one-sentence why. If the objective was never clearly stated, write
> "No explicit objective set" and infer the de facto purpose from the discussion.
>
> **TL;DR** — 2-3 sentences: the most important thing that happened and what it means for the group.
>
> **Decisions Made** — a table with columns: Decision | Rationale | Owner. Include only firm
> decisions, not discussion. If none, write "No formal decisions this session."
>
> **Action Items** — a table with columns: Action | Owner | Due (if stated). List every commitment
> made, with the named owner. Mark owner as "Unassigned" if no one was named.
>
> **Topics Discussed** — one bullet per topic. For each: a one-line summary, then the outcome tag in
> brackets — [Decided], [Needs follow-up], or [Parked]. Keep each to two sentences max.
>
> **Open Questions / Risks** — bullets for anything raised but unresolved, including who needs to
> weigh in to close it.
>
> **Artifacts Referenced** — list any docs, decks, diagrams, or links mentioned. Link each one to its
> org-readable location and label the link with the document's own title; where no published copy
> exists yet, give the file name and say so.
>
> Rules: Attribute decisions and actions to the specific person who owns them. Do not invent owners
> or dates. Skip pleasantries, tangents, and status updates that led nowhere. Write in plain, direct
> prose — no filler like "the team discussed the importance of." Keep the whole recap under one
> screen.

Load [Alex's voice](../../alex-voice/SKILL.md) (comms register) before drafting: this is internal comms in Alex's name.
No em dashes, with the `<h1>` title separator as the one documented exception (see below).

**Check it with `voice_check.py --register docs`, not comms** (measured both ways on the 2026-09-16
page). The comms register describes a message aimed at people (greeting, closer, exclamation marks);
this page is a written record.

So, reading the output:
- The **`?` warning is expected on every recap** and is not a defect. A question mark or an
  exclamation mark inside a recap means someone's voice leaked into the record.
- The **`<h1>` em dash is the one documented exception** and shows up as a BLOCKER in the checker,
  which does not know about the exception. Nothing else may be an em dash.
- **`The` sentence starts, sentence length and banned phrases are real signals.** Fix openers by
  rewording, never by dropping the article ("Git flow is not friendly" is fine; "Delay is ADP
  propagation" is not).
- **Voice edits on a recap are wording-only.** Never touch a fact, an owner, a tag or a quoted
  position to make a sentence read better. If a sentence is only fixable by changing what it claims,
  leave it and say so.

**Run `voice_check.py` on the RENDERED page text, not the content JSON.** The renderer's own
cosmetic characters count as prose; `render_page.py` now hard-fails on any em dash or en dash
outside the `<h1>`, but the rule stands for anything else. Two commands, no hand-rolled tag strip:

```sh
python3 references/render_page.py --text canvas.json > /tmp/page.txt
python3 ../alex-voice/scripts/voice_check.py /tmp/page.txt --register docs
```

`--text` reads the rendered canvas, so it also covers a canvas read back from SharePoint.

**voice_check exits 1 on a clean page, by design.** The pass condition is `BLOCKER: em dash x1` and
nothing else; two blockers, or a blocker naming anything but the em dash, is a real failure. Do not
read the non-zero exit as a failed page.

## Recap gates (on top of the prompt)

- **Write the Executive Summary band too.** It is generated from this recap and may not introduce a
  fact the recap does not carry. Full rules: [SKILL.md, Executive Summary](../SKILL.md#executive-summary--the-elt-readers-gate-new-2026-09-18).
  It goes through the review table as its own numbered line, and it is the line Alex reads most
  closely; `render_page.py` refuses a page without it, or a band outside 3 to 4 points, so a short
  band is a content fix, not an argument with the script.
- **The full exclusion screen applies to every line of the recap**, same as board rows: effect-side
  only, never a specific exposed endpoint, a live unremediated weakness, vendor-commercial posture,
  or personnel criticism. Where a topic cannot be described safely, drop it and tell Alex why rather
  than softening it onto the page.
- **Decision versus discussion is the highest-risk call.** An uncontested assertion is not a decision
  ("Alex asserted a scope boundary and nobody objected" is not the group deciding). Say what actually
  happened; a session ending with "let's circle back next week" is at best [Partially achieved].
- **Never invent an owner or a due date.** "Unassigned" and "Not stated" are correct answers;
  attribute to the person who spoke the commitment.
- **Artifacts Referenced carries links, not just filenames.** A reader must be able to go from the
  recap to the RFC, the ADR, the PR, or the deck behind an update.
  - **Link the primary record, not a folder:** a merged PR, an ADO item, the portfolio row, the
    published RFC/ADR/SAD, or the deck itself.
  - **Label with the document's own title, never an ID or raw URL.** Framework docs carry no
    identifier except `STANDARD-NNNN` and `ADR-NNNN`; there is no `RFC-0007` to cite, so the title is
    the identifier. Never invent an ID to make a link look tidy.
  - **Never link an unpublished doc.** Until it is in the Architecture Documents library it has no
    stable URL; name it and say it is not yet published. A 403 or a placeholder filename is worse
    than no link.
  - **The exclusion screen applies to the link target:** no personal-OneDrive URLs
    (`-my.sharepoint.com`), no access-restricted evidence, nothing the screen would keep off a row.
  - If the note names no artifact for a topic, leave it out; an invented link is a fabrication.
- **Do not print the recap into the terminal.** Generate it, verify it against the note, run
  `docs-reviewer`, address findings, stage it, and hand back **the link plus a short summary of what
  you fixed**. The staged draft is the review surface: Alex reads it rendered and clicks Publish
  there; a stored `CanvasContent1` read-back is no substitute for him seeing it.
- The recap does **not** go through the review table line by line; `PromotedState=1` is a draft
  nobody else sees, and Alex approves by publishing. Still in the review table: **intake close-outs,
  board rows, comments, and any judgment call you could not resolve** (a confidentiality trade-off, a
  finding against a house rule, a decision-versus-discussion call you are unsure about). Everything
  else you fix and report.
- A generated recap gives you the real `Outcomenotes` and the evidence to close out that session's
  AAB Intake items: propose those as review-table lines, never write them blind.

## Verify the draft against the note before showing it to Alex

Every one of these was a real error in the first generated recap (2026-08-26), caught by an
adversarial pass, not by re-reading. Run the check; do not trust the draft.

- **No spoken name means Unassigned.** Never derive an owner from who attended or whose ask it
  logically is; only a name spoken with the commitment becomes an owner.
- **Read the turns AFTER an apparent decision before recording it.** A scope boundary can be
  reversed in the very next turn (the 08-26 draft recorded a firewall boundary that the next
  speaker was already moving).
- **Cross-check the Decisions table against the Action Items table.** A settled row and an action
  to revisit it cannot both be true; it is the cheapest error to catch and the worst to publish.
- **Conditional agreement is not agreement.** Carry the condition or do not claim the agreement.
- **Driving the screen is not authorship.** Answering questions about your own artifact is not
  presenting it.
- **Never stitch two remarks into one quote.** Write prose when the phrasing spans utterances.
- **Decisions `Owner` = who made the call, not who will execute it.** On 2026-09-02 the draft
  credited Thomas Hofstetter and Job Lali with calls Alex had dictated; both said only "makes
  sense" / "gotcha". The Action Items table carries the executor. Name both people when one
  proposed and another accepted with conditions.
- **When the room contradicts itself about what a system IS, do not pick a side silently.**
  Describe it per the correction and attribute it, or leave the scope out.
- **Carry the counter-evidence, not just the loudest thread.** Report what narrows an objection
  (the 08-26 draft omitted the emergency change type, that the ticket never blocks the work, and
  that PCI already requires the recording).
- **A speaker with no visible contribution is a smell.** Diff the note's speaker list against the
  recap's names; on 08-26 the gap hid an action item's originator. Credit them or decide they
  added nothing.
- **Leadership criticism goes ownerless.** Keep the question, drop the people: "leadership has
  asked how we catch this ourselves."

Cheapest reliable form of this check (verified 2026-09-04): spawn **one** `general-purpose`
subagent on `sonnet` with the note path, the plain-text draft path, and all four lenses
(attribution, decision-versus-discussion, numbers and quotes, omissions and confidentiality), told
to return a `# | Lens | Recap text | Problem | Transcript evidence [hh:mm:ss] | Severity` table
and to find errors rather than approve. One agent with four lenses caught three attribution
BLOCKERs in ~2 minutes; four agents would re-read the same transcript four times. Keep the draft
as plain text (strip the HTML). Fix what it confirms, and tell Alex what you changed and why.

## Then run `docs-reviewer`, and address everything, before it goes anywhere

**Mandatory, every recap, no exceptions.** Note verification proves the recap is *true*;
`docs-reviewer` proves it is *readable*. They catch different things: the adversarial pass never
noticed that the Decisions table claimed four decisions while Topics Discussed tagged zero as
`[Decided]`, and it never noticed the recap was three times its own stated length limit.

Run it via the Skill tool (`attain-docs:docs-reviewer`) against the assembled page content, not the
markdown draft, so the shipped panel and the rendered structure are in scope. Then **fix every
BLOCKER and SIGNIFICANT finding before staging.** Do not hand Alex a review and ask what to do with
it; he asked for the finished thing. Bring him a decision only when a finding conflicts with an
established house rule (see the em-dash exception below) or when fixing it would change what the
meeting actually decided.

Known findings this review reliably surfaces on a first draft, so pre-empt them:

- **Outcome tags must actually vary.** If every topic is `[Needs follow-up]`, the tag carries no
  information. Any topic matching a Decisions row is `[Decided]`; make the tables and the tags agree.
- **Every Decisions row needs a matching topic bullet**, or the decision only exists in a table
  nobody reads twice.
- **Honour the "under one screen" line in the prompt.** A faithful record of a 90-minute meeting will
  not hit 400 words, but it should not hit 1,500 either. Merge topics that are one thread (the
  release model and the approval gap are the same story), and fold an open question into the topic
  that already covers it rather than saying it twice.
- **Do not bold both the topic lead-in and the tag** on every bullet. That is the inline-header
  vertical-list tell (humanizer 15 and 16). Lead-in bold, tag in the muted `#55636E`.
- **Do not repeat "Not stated" down a whole column.** Leave the cell empty and put one footnote under
  the table.
- **Keep attribution out of the action text.** "Proposed by X" belongs in the Owner cell.

> **Documented em-dash exception.** `docs-reviewer` flags every em dash as a BLOCKER, and the
> humanizer rule behind it is correct for prose. The `<h1>` title is the one allowed exception:
> `Architecture Weekly &mdash; Month D, YYYY` is the house format, fixed by the template and by
> Alex's own recap prompt, and eight published issues already use it. Keep it there and keep prose
> free of them. Do not re-litigate this every week; note the exception in your report and move on.
