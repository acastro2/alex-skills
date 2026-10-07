# HANDOFF: alex-skills

Updated: 2026-10-07 CDT. Full session history lives in the git history of this file (`git log -p docs/HANDOFF.md`).

## Current state

**Skill set (2026-10-07).** The repo keeps a skill only if it holds facts the model cannot know: how to use a tool, Alex's systems, or Alex's taste. Generic method skills were cut (tdd, grilling, codebase-design, domain-modeling, diagnosing-bugs, resolving-merge-conflicts, writing-for-agents, incident-remediation-reviewer, blog-reviewer, to-spec, to-tickets, herdr, typesafe-ai). New since then:

- `reviewer`: Alex's review lens (core checks from his CLAUDE.md), type layers in `references/` (code, docs, blog), grill rounds, a fixed shape for short messages. Code layer rebuilt from his own pre-Attain pr-reviewer (`git show 0eda409^:pr-reviewer/SKILL.md`). Do not copy the Attain plugin's pr-reviewer here: this repo pushes to personal GitHub.
- `search`: replaces find-docs and the three exa-* skills. Decision tree; Exa always through the MCP in Claude Code and OpenCode (the Claude Code sandbox blocks `api.exa.ai`); `curl` only in Pi, which has no MCP; Context7 CLI first.
- `jev`: the harness sends its own judgment calls to `ask_jev`. `references/eval-grading.md` grades eval expectations with Jev (61 of 62 firm verdicts matched reference grades). Alex removed the data-rule sections from `jev`, `search`, `bard`, `scribe`, and `archeologist` on 2026-10-07: his call, do not restore.

**Eval state.** Last runs, all with the safe flags in each `evals/README.md`: reviewer iteration-4 24/25 plus a one-run check of the message shape (163 words without the rewrite); search iteration-2 25/26 (dry run); jev iteration-1 with skill 23/24 vs baseline 11/24. Results: `~/.agents/skill-workspace/alex-skills/<skill>/iteration-N/`.

**Install layout.** `~/.claude/skills` is a real folder with one symlink per skill, not one symlink to this repo. Why: the claude.ai personal-skill sync writes `~/.claude/skills/synced/`, and with a whole-folder link that landed inside this repo, where OpenCode and Pi found a stale `alex-voice`. After adding or removing a skill, run `scripts/link_claude_skills.sh`.

**Instruction files** (`~/.claude/CLAUDE.md`, `~/.config/opencode/AGENTS.md`, `~/.pi/agent/AGENTS.md`) point at `search` and `jev`; the `# Skills` section is gone from Claude and OpenCode; `~/.claude/rules/context7.md` is a pointer to `search`.

**alex-voice rebuild v2 (in progress since 2026-10-02).** Done means a blind lineup where Alex picks the fakes at chance. All identity marks so far: 27 of 48 caught (56%, p=0.24): passes overall; weak spot is spoken (5 of 6 caught, small n). Eval iteration-5: 290/293. Round 3 lineup workflow `wf_7113c18f-530` was built; its marking status is not recorded. Private corpus, findings, and lineup notes: `~/Developer/obsidian/Alex/40 Writing/Voice/` (never in this repo).

**scribe and bard go daily (2026-10-01).** scribe runs transcription as a pool (`hidock_batch.sh`, jobs default 3) and per-meeting summary subagents. Per-source cursors live in `.scribe-state.json`; bard selects scribe notes by a `scribe_seen` set in `Bard/.bard-state.json`, seeded on the first daily `/bard`.

**ea-projects-curator Jev gates (2026-09-29 to 10-01).** Five typed gates per candidate; 12 Jev findings applied by Alex. Report: `.scratch/jev-board/report.md`.

## Top 3 next actions

1. **Check that skills auto-load.** Managed `syncClaudeAiPlugins: false` is live: the skill list dropped from 466 to 147 (checked 2026-10-07 with a `claude -p` init event). Still to check: in a fresh interactive session, "review this…" loads `reviewer` without being named. Before the change it triggered 0 of 24 times, because the list was too long for the descriptions to fit.
2. **alex-voice round 3:** find out whether Alex marked the round 3 lineup; if so, score his picks against the key and turn each miss into a rule.
3. **First live daily run:** after the next `/scribe` and `/bard`, check `.scribe-state.json` (both cursors) and `Bard/.bard-state.json` (`scribe_seen` seeded). The scribe transcription pool has not run on a real batch yet.

## Blockers and open decisions

- Alex only: delete the old `alex-voice` and `skill-creator` from claude.ai → Customize → Skills. Until then Claude Code lists a stale `anthropic-skills:alex-voice`.
- Curator row 46 ("Engineering Intelligence Service Identities"): AI Program or Governance? Alex to confirm.
- Whether to add more Jev questions to the curator (impact kind, outcome at close).
- Three questions from an earlier Jev session still block the corpus and shortlist work (not the curator): what "EA intake" means in Alex's words, which corpus to classify, and what produces the shortlist.

## Pointers

- Jev: `~/.local/bin/jev` (CLI), `~/.local/bin/jev-mcp` (MCP server `jev`, tool `ask_jev`), registered in `~/.config/opencode/opencode.jsonc` and `~/.claude.json`; model `jev-1.13-free` on OpenCode Zen. A `score` answer is a position on the scale: read the lean, not the nearest integer.
- Eval runner with the safe flags (no MCP, no shell, kills the process group): `~/.agents/skill-workspace/alex-skills/search/iteration-1/trigger/run_eval.py`. Its skill-match check is written for `search`.
- `SKILL.md` gotcha: Claude Code replaces a dollar sign followed by a digit with the skill's arguments. Write prices as `USD 0.10`.
- Stuck OpenCode session, read-only diagnosis: `ses_f12264570ffeHIM8tJj2BWDNfG` fails with "OpenAI Chat assistant messages only support text, reasoning, and tool-call content"; untested fix: switch its model back to `claude-code/claude-opus-5-5`.
- scribe diarization (Phase 1 shipped, voiceprinting rejected): `ses_f2b19eaa6ffeGBIQnPXt6q27xw`, `.scratch/scribe-diarization/`.
