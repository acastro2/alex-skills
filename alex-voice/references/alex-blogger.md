# Alex's Voice: Blog Posts

> Extends `../SKILL.md`. Read that first. Numbers come from `voice-fingerprint.md`.
> Score every draft: `python3 ../scripts/voice_check.py <draft.md> --register blog`.

## Which Alex the blog sounds like

The target is the voice of the posts Alex wrote by hand and lightly polished in 2023 and 2024 (the Kafka retries post and the first two Senior Engineer parts). Not the 2025 to 2026 posts, which were AI-drafted and carry 44 to 141 em dashes per 10k words, "Here's the thing" openers, and one-line drama paragraphs.

What the 2023 to 2024 posts measure, and the blog targets that follow:

| Metric (per 10k words) | 2023 to 2024 posts | 2025 to 2026 AI drafts | Target |
| --- | --- | --- | --- |
| avg words per sentence | 14 to 19 | 13 to 18 | 14 to 21, one long thinking sentence per section is good |
| p90 words per sentence | 27 to 34 | 23 to 33 | up to 42 |
| `?` | 35 to 49 | 4 to 114 | 30 to 80 |
| `!` | 31 to 88 | 4 to 33 | 15 to 70 |
| `(` asides | 124 to 253 | 33 to 138 | 60 to 220 |
| em dash | 13 to 39 (2024 polish, remove) | 44 to 141 | 0 |
| "you" as % of words | 1.6 to 4.7 | 0.9 to 3.5 | 2 or more |
| sentences starting with "The" | 8% | 14% | under 10% |

Keep from the early posts: second person, exclamation marks, parenthetical asides, tag questions ("right?"), "In my honest opinion", "Cool, but", "Let me diagram that", "To my surprise, this approach worked!", "let's build our own!", the WARNING callout with the honest trade-off, and the "When not to use this pattern" section.

Drop from them: em dashes, "Spoiler alert", "The truth is", "Here's the deal" (all three came from the 2024 polish pass, not from Alex).

## Brand context

Positioning: Platform Toolsmith, the architect who still ships code. Tagline on the site: "Platform Architect at a Chicago fintech. 15+ years shipping systems that handle real money." Manifest: architecture should ship, not just spec.

Audience: engineering leaders and senior engineers at Series C+ companies, plus the seniors and tech leads who read the career series.

Three streams, all under the Toolsmith brand:

1. **Platform and executable architecture.** Internal platforms, golden paths, ADRs as code, fitness functions, observability, Kafka, Terraform, Kubernetes.
2. **AI-native architecture and agent tooling.** Running coding agents at enterprise scale, skills and plugins as the new internal platform, agent guardrails, AI code review, what changes for architects when the team is people plus agents.
3. **Career and mentoring.** The Senior Engineer series and what comes after it, told from a principal-turned-VP who still codes.

Content formula: What I built or learned, why it mattered, how you can too. The blog is a portfolio that happens to be readable.

## Openings, verified from real posts

Alex opens with the reader's situation or the pain, in the second person, and often with a tag question. Never with a definition, history, or a broad claim.

- Technical, pain first: "You don't 'need retries in Kafka' until the day one of your handlers starts failing and you're forced into a choice: block consumption (and watch lag climb) or keep consuming and retry somewhere else."
- Mentor, recognition first: "Hey there! First off, take a moment to celebrate. You've earned the rank of Senior Engineer. That's no small feat." His 2023 hand draft of the same idea: "OK, you are a senior, now what?"
- Question that names the elephant: "Cool, but, this is a blog post about retries right? Where are the retries in all of it?"

Never open with "Retry logic is...", "Since the early days of...", or "In today's microservices world...".

## Structure

### Technical posts

```
Hook: the reader's pain or a surprise, second person
Context: what you'll get, one paragraph, honest scope ("this post is explicitly about X, not Y")
Example world: "Imagine you work for a company named ACME..." plus a mermaid diagram
The journey: what I tried first and why it fell short (SQS, Kafka itself, a database...)
What worked: design, code, diagram
The trade-off, in a WARNING callout: what you give up, when not to use this
So what now: next step for the reader, link to the repo
```

### Mentoring posts

```
Hook: recognition of where the reader is, then the redirect
Validate the struggle: "This is hard, and here's why"
The insight from experience, with a real (anonymized) story
Make it actionable: a short list the reader can do this quarter
Encourage, then the mentoring CTA
```

### Structural rules

- H2 sparingly, 4 to 6 per post, plain descriptive wording. No catchy headers (his correction: "too catchy, feel a bit artificial, just make it like standard wording").
- Paragraphs are 2 to 5 sentences. One-sentence paragraphs are for a real turn, at most one per section.
- Mermaid in every technical post, introduced with "Let me diagram that" or "Let's diagram that for more visibility". Cap at about 10 nodes.
- Code is realistic and runnable, language-tagged, with imports. Comments only where the why is not obvious.
- Callouts: NOTE for context, TIP for the shortcut, WARNING for the trade-off that can bite. The WARNING is where the honesty lives.
- Before and after comparisons: show the bad version first, then the better one and why.
- Titles are specific and searchable: technology plus outcome. "Kafka Retries: Implementing Consumer Retry with Go", not "My Thoughts on Message Queues".

## Teaching moves, verified

- **Lower the resolution first.** "Quick context (assuming you already speak Kafka): consumer groups split partitions across consumers." Then add detail.
- **Build an example world.** "Imagine you work for a company named ACME, and you have a Kafka topic that receives a new message every time a new customer is created."
- **Ask the question the reader is thinking, then answer it.** "Cool, but... where are the retries in all of it? Well, any part of the processing can go wrong, and we don't want our customers to miss out on their emails, do we?"
- **Show the failed attempts with feeling.** "Desperate Times Call for Desperate Measures, right? As a last resort, I turned to databases. To my surprise, this approach worked! However, it's not a perfect solution."
- **Give the honest tool opinion.** "In my honest opinion, the Spring Kafka framework offers a flexible approach that is well worth considering." "I currently work with (and love) Go."
- **Name when not to use it.** A "When not to use this pattern" section beats a caveat buried in prose.
- **Translate tech to business when the reader has to pitch it.** Current pain plus risk versus migration cost, in one line.
- **Coin a name only when it helps the reader remember**, and keep it plain ("The Senior Loop" is fine; a buzzword is not).

## Technical versus mentor mode

| Dimension | Technical | Mentor |
| --- | --- | --- |
| Opening | pain or surprise, second person | "Hey there!", recognition then redirect |
| Authority | "I built this", "we shipped this" | "engineers I mentor", "when I was in your position" |
| Analogies | systems: pipes, queues, circuits | life and games: tutorial level, leveling up, boss fights |
| Vulnerability | "I tried X and it failed" | "I lost a promotion to someone with half my depth", "if you are not uncomfortable you are doing it wrong" |
| Phrases that are his | "Cool, but", "Let me diagram that", "To my surprise", "In my honest opinion" | "trust me", "Don't get me wrong", "congratulations!", "you are just a more senior senior" |
| Code | yes, realistic | rarely, only as illustration |
| Close | "try this in your codebase", repo link | "talk to your manager about...", mentoring link |
| Emoji | sparse: clap, warning, heart at the very end | clap at the congratulations, heart at the end |

## Sanitization (critical for anything from work)

Strip: employer names, team names, colleague names, internal tool names (describe by function), internal URLs, ticket numbers, customer and partner names, exact revenue or user counts (percentages are fine), proprietary logic.

Keep: open source tools, general patterns, sanitized code, the problem shape. If a detail could identify a person or a decision even with names removed, cut it. When in doubt, ask Alex before drafting.

## Series coherence

- Same opening energy across parts ("Hey there!").
- Reference earlier parts naturally ("In Part 1 we talked about...").
- Each part stands alone but rewards reading in order. End with a link block to the series.

## Self-review checklist

- [ ] Opens with the reader's pain or situation, not a definition
- [ ] At least one real question in the first three paragraphs
- [ ] At least one personal story with specific detail (sanitized)
- [ ] At least one opinion that starts with "I think", "to me", or "in my honest opinion" and then says the thing
- [ ] A journey: what was tried first and why it fell short
- [ ] A WARNING or "when not to use this" with the honest trade-off
- [ ] Mermaid diagram (technical) or a concrete practice list (mentor)
- [ ] Exclamation marks and parentheses present; em dashes absent; never-use list clean
- [ ] Paragraphs of 2 to 5 sentences, headers plain, title searchable
- [ ] `voice_check.py --register blog` shows no BLOCKER
- [ ] Read aloud: does it sound like Alex explaining over coffee, not a blog template?

## The differentiation test

1. Could a career coach who never shipped production code write this? Add platform grounding.
2. Could a technical writer who never managed people write this? Add the mentoring experience.
3. Could anyone on LinkedIn have posted this? Add something only Alex knows.
4. Does it show the journey or only the destination? Add the failed attempts.
