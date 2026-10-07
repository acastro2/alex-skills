# Blog layer

Load `../../alex-voice/references/alex-blogger.md` first. It owns the brand, audience, voice, and the self-review checklist, including `voice_check.py --register blog`. This file adds only the review checks it does not have.

## Strategic fit

- Does it show something Alex built and shipped, or only opinion? Theory with no build is a Should-fix; a post anyone could write is a Blocker.
- Would a platform or engineering leader at a Series C+ company finish it and want to talk to him?
- Does it give the reader something they can do: the build, why it mattered, how they can do it too?

## Technical credibility

- Code must be correct and would pass Alex's own code review. Wrong code is a Blocker.
- Trade-offs say why X over Y. Production gotchas and lessons are the value; keep them.
- No claim without evidence or reasoning. A staff engineer reading it must find nothing to dismiss.

## Discoverability

- Title names the specific technology and the specific outcome, in standard wording, not a catchy hook.
- H2s let a skimmer get the structure.

## Sanitization: any hit is a Blocker

- Employer names (Enova, Attain, or any other)
- Team, colleague, customer, or partner names
- Internal tool names, URLs, channels, tickets
- Revenue or user counts (percentages are fine)
- Proprietary business logic
