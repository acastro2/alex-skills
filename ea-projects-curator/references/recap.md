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

`scribe` already applies the glossary at `<vault>/Scribe/Glossary.md` to known garbles (Lucidchart,
FireMon, Ivanti, ADO, CURO, Five9, SE), so most of the noise is gone before you read the note. You
still verify every remaining proper noun in the note against what you can confirm — correct only
what you can confirm, otherwise describe the thing without naming it — and if you confirm a new
garble the glossary missed, append it to `<vault>/Scribe/Glossary.md` as a `- wrong => Right` line.
That glossary file is the one scribe-owned file the curator may append to. The note may also end
mid-sentence if the source transcript did. Say so in the recap footer rather than inventing an ending.

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

**Check it with `voice_check.py --register docs`, not comms.** Measured both ways on the rendered
`2026-09-16` page (2026-09-18). Under **docs** the page throws one warning; under comms it throws
three that do not apply. The comms register describes a message aimed at people (greeting, closer,
exclamation marks); this page is a written record. Calibrate against the published issues too:
`2026-09-09-AAB-Recap.aspx` has **0 question marks, 0 exclamation marks and 1 em dash** (the `<h1>`
separator) in 1,408 words.

So, reading the output:
- The **`?` warning is expected on every recap** and is not a defect. A question mark or an
  exclamation mark that appears inside a recap means someone's voice leaked into the record.
- The **`<h1>` em dash is the one documented exception** and shows up as a BLOCKER in the checker,
  which does not know about the exception. Nothing else may be an em dash.
- **`The` sentence starts, sentence length and banned phrases are real signals.** The 2026-09-18 pass
  on the 09-16 page found 12 sentences opening with "The" and fixed them by rewording the opener
  only; the rate went from 7.6% to 1.1%. Fix openers by rewording, never by dropping the article
  ("Git flow is not friendly" is fine; "Delay is ADP propagation" is not).
- **Voice edits on a recap are wording-only.** Never touch a fact, an owner, a tag or a quoted
  position to make a sentence read better. If a sentence is only fixable by changing what it claims,
  leave it and say so.

**Run `voice_check.py` on the RENDERED page text, not the content JSON.** The renderer's own
cosmetic characters count as prose: on 2026-09-18 an em dash used as the empty-cell placeholder in
the Action items table passed a JSON-only check and was caught only by reading the rendered page.
`render_page.py` now hard-fails on any em dash or en dash outside the `<h1>`, so that one cannot
come back, but the rule stands for anything else. Two commands, no hand-rolled tag strip:

```sh
python3 references/render_page.py --text canvas.json > /tmp/page.txt
python3 ../alex-voice/scripts/voice_check.py /tmp/page.txt --register docs
```

`--text` reads the rendered canvas, so it also covers a canvas read back from SharePoint.

**voice_check exits 1 on a clean page, by design.** The `<h1>` em dash is a BLOCKER to the checker,
which does not know about the exception. The pass condition is `BLOCKER: em dash x1` and nothing
else. Two blockers, or a blocker naming anything but the em dash, is a real failure. Do not read the
non-zero exit as a failed page.

## Recap gates (on top of the prompt)

- **Write the Executive Summary band too — it is part of this deliverable.** The page opens with a
  band for the executive leadership team, who read the page but were not in the room. It is generated
  from this recap and may not introduce a fact the recap does not already carry. Full rules are in
  [SKILL.md, Executive Summary](../SKILL.md#executive-summary--the-elt-readers-gate-new-2026-09-18):
  one plain-words `headline`, 3 to 4 bold-lead `points`, and a `footer` that says whether leadership
  must act. It goes through the review table as its own numbered line, and it is the line Alex reads
  most closely. `render_page.py` refuses to render a page without it, and refuses a band outside 3 to
  4 points, so a short band is a content fix and not a thing to argue with the script about.
- **The full exclusion screen applies to every line of the recap**, same as board rows. The forum
  discusses live security detail; the recap is org-visible. Keep it effect-side: never name a
  specific exposed endpoint, a live unremediated weakness, vendor-commercial posture, or personnel
  criticism. Where a topic cannot be described safely, drop it and tell Alex why in your report
  rather than softening it onto the page.
- **Decision versus discussion is the highest-risk call.** Promoting an uncontested assertion into
  "Decided" misleads everyone who reads it. If Alex asserted a scope boundary and nobody objected,
  that is not the same as the group deciding; say what actually happened. When the session ends with
  "let's circle back next week," the Outcome is at best [Partially achieved].
- **Never invent an owner or a due date.** "Unassigned" and "Not stated" are correct answers.
  Attribute to the person who actually spoke the commitment.
- **Artifacts Referenced carries links, not just filenames.** This is the traceability line: a reader
  must be able to go from the recap to the RFC, the ADR, the PR, or the deck behind an update.
  - **Link the primary record, not a folder.** A merged PR, an ADO item, the portfolio row, the
    published RFC/ADR/SAD, or the deck itself.
  - **Label with the document's own title, never an ID and never a raw URL.** Framework docs carry
    no identifier except `STD-NNNN` and `ADR-NNNN`, so there is no `RFC-0007` to cite — the title is
    the identifier. Never invent an ID to make a link look tidy.
  - **Never link an unpublished doc.** Until the file is in the Architecture Documents library it has
    no stable URL. Name it and say it is not yet published. A link that 403s or lands on a
    placeholder filename is worse than no link.
  - **The exclusion screen applies to the link target.** No personal-OneDrive URLs
    (`-my.sharepoint.com`), no access-restricted evidence, nothing the screen would keep off a board
    row.
  - If the note names no artifact for a topic, leave it out. An invented link is a fabrication like
    any other.
- **Do not print the recap into the terminal.** Alex does not read it there, and a 1,300-word page
  pasted into a CLI is noise. Generate it, verify it against the note, run `docs-reviewer`,
  address the findings, stage it to SharePoint, and hand back **the link plus a short summary of
  what you fixed**. The staged draft is the review surface: he reads it rendered, where the layout
  problems are actually visible, and clicks Publish there. Reading back the stored
  `CanvasContent1` is not a substitute for him seeing it.
- The recap therefore does **not** go through the numbered review table line by line; staging it is
  safe because `PromotedState=1` is a draft nobody else sees, and he approves by publishing. What
  still goes in the review table: **intake close-outs, board rows, comments, and any recap judgment
  call you could not resolve yourself** (a confidentiality trade-off, a finding that conflicts with
  a house rule, a decision-versus-discussion call you are not sure about). Everything else you fix
  and report.
- A generated recap also gives you the real `Outcomenotes` for that session's AAB Intake items and
  the evidence to close them out. Propose those as review-table lines too, never write them blind.

## Verify the draft against the note before showing it to Alex

Every one of these was a real error in the first generated recap (2026-08-26), caught by an
adversarial pass, not by re-reading. Run the check; do not trust the draft.

- **No spoken name means Unassigned.** "Take one person from your team and ask them to try it" said
  to the room is not an assignment to the four managers you infer were present. Never derive an
  owner from who attended, who runs a team, or who the ask logically lands on. Only a name actually
  spoken in connection with the commitment becomes an owner.
- **Read the turns AFTER an apparent decision before recording it.** A scope boundary Alex states
  can be reversed in the very next turn. In the 08-26 draft "firewall changes stay out of ITCC" was
  recorded as decided while the next speaker offered to move firewall tracking IN and drop the
  separate product, which made the recap contradict itself.
- **Cross-check the Decisions table against the Action Items table.** If a row says something is
  settled and an action item says someone is looking into changing it, one of them is wrong. That
  contradiction is the cheapest error to catch and the most embarrassing to publish.
- **Conditional agreement is not agreement.** "I agree, but it still needs X" is a condition; carry
  the condition or do not claim the agreement.
- **Driving the screen is not authorship.** Alex demoing someone's ticket does not make it his, and
  someone answering questions about their own artifact did not necessarily present it.
- **Never stitch two remarks into one quote.** If the phrasing spans utterances minutes apart, write
  it as prose, not as a quotation.
- **Decisions `Owner` = who made the call, not who will execute it.** On 2026-09-02 the draft
  credited Thomas Hofstetter with "audit log to Loki" and "signing keys in Secrets Manager", and Job
  Lali with the check-in cadence; the transcript shows Alex dictating all three and them saying
  "makes sense" / "gotcha". The Action Items table is where the executor's name belongs. When one
  person proposed and another accepted with conditions, name both with what each contributed
  ("Thomas Hofstetter (OpenIddict), Alexandre Castro (JWTs alongside)").
- **When the room contradicts itself about what a system IS, do not pick a side silently.** The
  presenter called Tiger Auth "internal only"; Flor said it also authenticates customers. A recap
  that repeats the first as fact is wrong on the record. Describe the system per the correction and
  attribute the correction, or leave the scope out.
- **Carry the counter-evidence, not just the loudest thread.** A recap that reports only the
  pushback misrepresents the room. The 08-26 draft omitted the emergency change type, the fact the
  ticket never blocks the work, and that PCI already requires recording cardholder-environment
  changes; all three narrow the overhead objection it led with.
- **A speaker with no visible contribution is a smell.** Diff the note's speaker list against
  the names appearing in the recap. On 08-26 that gap hid the originator of an action item, credited
  to Alex instead. Either credit them or knowingly decide they added nothing.
- **Leadership criticism goes ownerless.** "Rick asked me why we didn't know before they did" names
  a senior leader challenging a named manager over a security miss. Keep the question, drop the
  people: "leadership has asked how we catch this ourselves."

Cheapest reliable form of this check (verified 2026-09-04): spawn **one** `general-purpose`
subagent on `sonnet` with the note path, the plain-text draft path, and all four lenses
(attribution, decision-versus-discussion, numbers and quotes, omissions and confidentiality), told
to return a `# | Lens | Recap text | Problem | Transcript evidence [hh:mm:ss] | Severity` table and
to find errors rather than approve. One agent with four lenses caught three attribution BLOCKERs
in ~2 minutes for ~95K tokens; four agents would have re-read the same 43-minute transcript four
times. Keep the draft as plain text (strip the HTML) so the verifier reads what a reader reads.
Fix what it confirms, and tell Alex what you changed and why.

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
