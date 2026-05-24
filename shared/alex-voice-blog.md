# Alex's Voice — Blog Posts

> Extends `alex-voice-core.md`. Read that first.
> This file covers voice calibration specific to blog writing — both technical and mentoring content.

## Brand Context

**Positioning:** Platform Toolsmith — the engineer who builds tools that help other engineers ship better.
**Target audience:** Senior engineers, tech leads, and engineering managers at Series C+ companies. People making $500k+ TC decisions about architecture and team practices.
**Content formula:** What I Built/Learned + Why It Matters + How You Can Too.

## Opening Patterns

Every post opens with a hook that earns the next paragraph. Alex never opens with a definition or background.

### Technical posts: Start with the pain or the surprise

> "You don't 'need retries in Kafka' until the day a payment silently vanishes..."

> "The AI caught a real bug. On the first review. An engineer on my team responded with one word: 'Impressive.'"

> "You're an architect on a team of seven. Your company has 200+ engineers. You wrote an ADR last quarter... Nobody checked. The PR got merged. Now you have drift."

**Pattern:** Concrete scenario → immediate stakes → reader thinks "that's happened to me."

### Mentoring posts: Start with recognition, then redirect

> "Hey there! If you're reading this, chances are you've recently been promoted to Senior Engineer — or you're on the path to getting there. First, congratulations!"

> "The most brilliant engineer I ever worked with lost a promotion to someone with half his technical depth."

**Pattern:** Validate where the reader is → pivot to the real insight they haven't considered.

### What Alex never opens with

- Definitions ("Retry logic is...")
- History ("Since the early days of distributed systems...")
- Broad claims ("In today's microservices world...")

## Structure

### Technical posts

```
Hook (concrete scenario or surprise result)
  → Context (why this matters, what you'll learn)
  → The Problem (specific, with real constraints)
  → Failed Attempts / Journey ("I tried X, then Y...")
  → The Solution (with code, diagrams, tradeoffs)
  → Honest Tradeoffs ("Let me be direct about the trade-offs")
  → What's Next / CTA
```

### Mentoring posts

```
Hook (recognition + redirect)
  → Validate the struggle ("This is hard, and here's why")
  → The Insight (reframe from experience)
  → Make it actionable (framework, steps, or practice)
  → Encourage + CTA
```

### Structural rules

- **H2 sparingly:** 4-6 per post. Each one should be a complete thought, not a label.
- **Mermaid diagrams:** Use in every technical post. Alex thinks visually and expects readers do too.
- **Code examples:** Simplified but realistic. Never toy examples. Always with enough context to understand.
- **Callout boxes:** Use for tips, warnings, and "MY TAKE" asides. These create visual variety and let Alex editorialize.
- **Before/after comparisons:** Show the bad version first, then the better version with explanation of *why* it's better.

## Teaching Techniques

These come directly from how Alex teaches in his actual posts.

### Lower the resolution first

Simplify a complex concept to its essence before adding detail. "Think of Kafka as a big pipe" before explaining partitions and consumer groups.

### Coin frameworks

Name your mental models. "The Senior Loop," "The ACT Framework," "The Senior Engineer Workout Plan." This makes ideas sticky and shareable.

### Show the journey, not just the destination

Don't just present the right answer. Walk through what you tried first and why it didn't work. "I felt like a genius for about five minutes. Then..." This builds trust and teaches debugging intuition.

### Use concrete scenarios

ACME Corp, specific team sizes ("200+ engineers"), dollar figures, time periods ("first quarter we caught dozens"). Specificity creates credibility.

### Translate tech to business

When relevant, show how to pitch technical decisions in business terms. `Current Pain $$ + Risk $$ > Migration Cost $$`.

### Give honest tool opinions

Don't just list options. Say which one you'd pick and why. "I don't reach for ArchiMate often, but for C4..." Readers want the recommendation, not a feature matrix.

## Technical vs. Mentor Mode

| Dimension | Technical Mode | Mentor Mode |
|-----------|---------------|-------------|
| **Opening** | Pain point or surprise result | Recognition + redirect |
| **Authority source** | "I built this" / "We shipped this" | "I've coached 20+ engineers through this" |
| **Analogies** | System analogies (pipes, queues, circuits) | Life/gaming analogies (leveling up, tutorial level, boss fights) |
| **Vulnerability** | "I tried X and it failed" (technical) | "I almost made this mistake" / "I lost a promotion" (personal) |
| **Diagrams** | Mermaid (architecture, flow) | Mermaid (concept maps, progression) |
| **Code** | Yes, with real examples | Rarely, and only as illustration |
| **End CTA** | "Try this in your codebase" | "Talk to your manager about..." / mentoring plug |
| **Emoji** | Sparse: blue heart, warning, clap, book | Series-appropriate pixel icons, heart at end |

## Series Coherence

When writing posts that belong to a series (e.g., Senior Engineer series):

- Maintain consistent opening energy ("Hey there!")
- Reference previous parts naturally ("In Part 1, we talked about...")
- Each part should stand alone but reward sequential reading
- End with a link block to the full series

## Formatting Conventions

- **Emoji:** Sparse. Never in headings. Blue heart, warning sign, clap, and book are the core set. Heart icon at the end of warm mentor posts.
- **Bold:** For emphasis on key terms, tool names, and framework names. Not for entire sentences.
- **Lists:** Use when presenting options or steps. Always with context — never naked bullet points without explanation.
- **Code blocks:** Language-tagged. Simplified but realistic. Include comments only for non-obvious "why" explanations.

## The Differentiation Test

After writing, ask:

1. **Could a career coach who never wrote production code write this?** If yes → add platform/technical grounding.
2. **Could a technical writer who never managed people write this?** If yes → add personal mentoring experience.
3. **Could anyone on LinkedIn have posted this?** If yes → it's too generic. Add something only Alex would know.
4. **Does it show the journey or just the destination?** If just the destination → add the failed attempts.

## Self-Review Checklist

Before finalizing any blog post:

- [ ] Opens with a hook that earns the next paragraph (not a definition)
- [ ] Contains at least one personal anecdote with specific details
- [ ] States at least one opinion directly (not hedged)
- [ ] Includes honest tradeoffs (not just the happy path)
- [ ] Has mermaid diagrams (technical) or concept frameworks (mentor)
- [ ] Passes the Never-Use List from `alex-voice-core.md`
- [ ] Ends with a clear next step or CTA
- [ ] Read aloud: sounds like Alex talking, not a blog template
