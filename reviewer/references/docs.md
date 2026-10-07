# Docs layer: ADRs, RFCs, runbooks, guides, specs

Load `../../alex-voice/SKILL.md` first for the core voice rules and the never-use list, then `../../alex-voice/references/registers/docs.md`, and use its rules, red flags, and test as the checklist: why on every step that is not obvious, one recommended path, an expected result for each step, ADR context and reversal, and "can a new teammate follow it alone?". That file was written for drafting, so read each rule as a question about the doc in front of you.

For an Attain Enterprise Architecture doc (ADR, RFC, STANDARD, RUN, SOW, SAD, BRIEF), also load the EA doc framework skill if it is available (`ea-doc-framework`, or `docs-reviewer` for its hard rules). It owns the rules for each doc type. When it is loaded, its type definitions win over check 1 below.

Then add the checks below. The register does not cover them, because they only show up when you review.

## Review-only checks

1. **Is it the right doc type?** A proposal that asks for a decision is an RFC, not an ADR. A record of a decision already made is an ADR. Steps an on-call engineer runs are a runbook, not a design doc. The wrong type sets the wrong expectations for the reader and the wrong review path. Wrong type is a Should-fix; a doc that asks for a decision while it claims the decision is made is a Blocker.
2. **What is the ask, from whom, by when?** An RFC or proposal must say what decision it needs, who makes it, and the date it is needed by. With no ask, nobody acts and the doc goes stale. Missing ask is a Blocker for an RFC or proposal.
3. **Pointers, not copies.** Content copied from the code, another doc, an ADR, or a wiki goes stale the day the source changes. Flag copied config, schemas, step lists, and decisions, and replace each with a link or a path to the source. Keep a copy only when the reader cannot reach the source.
4. **Current and owned.** Check that commands, paths, links, and names still exist where you can verify them (read the repo, run a read-only command). Flag a step that refers to something that no longer exists as Confirmed. The doc must route the reader to a person or a channel when it does not cover their case.
5. **Rejected options for a decision.** An ADR or RFC names the options it did not pick and why each lost. Without them, the forum re-argues the same options and the next reader cannot tell if they were considered. Missing options is a Should-fix; for a decision that is hard to reverse it is a Blocker.
6. **One question per doc.** A doc that answers two questions (a design and its runbook, a decision and a tutorial) gets read for one and missed for the other. Recommend the split and say which part goes where.

## Output additions

Name the doc type you reviewed it as on the line after the verdict, so the author sees it when your type and theirs differ.
