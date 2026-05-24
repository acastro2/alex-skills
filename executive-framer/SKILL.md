---
name: executive-framer
description: "Frame technical initiatives, findings, and decisions for executive and board audiences. Use when presenting to leadership, justifying investment, framing for the CEO, preparing a board update, explaining cost rationalization, translating risk for non-technical stakeholders, writing an executive summary, or when someone asks 'how do I present this to leadership'. Produces presentation-ready outputs that connect every point to cost, risk, or revenue impact."
---

# Executive Framer: Stakeholder Communication Playbook

Your documented patterns for communicating technical work to leadership based on analysis of 86+ executive-focused sessions.

## When to Use This Skill

- Justifying technology investments or new tooling spend
- Reporting adoption metrics and progress dashboards
- Presenting architecture decisions to leadership
- Translating technical debt into business risk
- Framing vendor evaluations for executives
- Creating 5-slide presentations for leadership reviews

---

## PE-Backed Financial Services Communication Context

### The Fundamental Rule
**The CEO views technology as a cost center.** Every output from this skill must answer one of:
- How much does this **cost** and why is it worth it?
- What **risk** does this address and what's the exposure in dollars?
- How does this **protect or grow revenue**?

Technical excellence, best practices, and industry standards are *supporting evidence*, never the headline.

### PE-Specific Communication Patterns
1. **Quantify everything** - "Significant improvement" → "$340K annual savings". No unquantified claims.
2. **Compress timelines** - PE expects 12-18 month payback. If your timeline is longer, explain why and what interim value is delivered.
3. **Show vendor consolidation** - Any opportunity to reduce vendors gets attention. Lead with it.
4. **Benchmark against portfolio** - PE firms compare across portfolio companies. Frame metrics as "we are at X, portfolio median is Y."
5. **Audit readiness sells** - In regulated financial services, "audit-ready" translates to "won't slow down our next transaction."

### Board Update Template
Use when preparing materials for board meetings or PE sponsor reviews:

```markdown
# Technology Update — [Quarter/Date]

## Key Metrics (Traffic Light)
| Metric | Status | Current | Target | Trend |
|--------|--------|---------|--------|-------|
| Infrastructure spend vs budget | 🟢/🟡/🔴 | $X | $Y | ↑↓→ |
| System uptime (revenue-critical) | 🟢/🟡/🔴 | X% | 99.9% | ↑↓→ |
| Audit findings open | 🟢/🟡/🔴 | N | 0 | ↑↓→ |
| Vendor count | 🟢/🟡/🔴 | N | Target | ↑↓→ |
| Mean time to recover | 🟢/🟡/🔴 | Xh | Yh | ↑↓→ |

## What Changed This Quarter
[3-4 bullets, each with $ impact]

## What's At Risk
[2-3 bullets, each with $ exposure if not addressed]

## Asks
[Specific asks with $ amounts and expected returns]
```

### Cost Rationalization Narrative Template
Use when presenting infrastructure cost reduction or vendor consolidation plans:

```markdown
# Technology Cost Rationalization — [Initiative Name]

## Current State
- Total technology spend: $X/year
- Benchmark (industry/portfolio): $Y/year  
- Gap: $Z/year (N% above benchmark)

## Reduction Opportunities (Ranked by Confidence)

### Quick Wins (0-3 months, high confidence)
| Opportunity | Annual Savings | Effort | Confidence |
|-------------|---------------|--------|------------|
| [Item] | $X | Low/Med/High | High |

### Medium-Term (3-9 months, medium confidence)
| Opportunity | Annual Savings | Effort | Confidence |
|-------------|---------------|--------|------------|
| [Item] | $X | Low/Med/High | Medium |

### Strategic (9-18 months, requires investment)
| Opportunity | Annual Savings | Investment Required | Payback Period |
|-------------|---------------|--------------------|----|
| [Item] | $X/year | $Y one-time | N months |

## Total Projected Savings
- Year 1: $X (quick wins + partial medium-term)
- Year 2: $Y (full run-rate)
- 3-Year cumulative: $Z

## Risks to Achieving Targets
[2-3 bullets with mitigation]
```

---

## Situation Types & Templates

### 1. Executive Summary (For CTO/VP Review)

**Use when**: Dashboard is ready, tool is built, initiative needs sign-off

**Template Structure**:

```markdown
# Executive Summary: [Initiative Name]

## TL;DR (One Paragraph)
[What it is] + [Business value] + [Current status] + [What you need]

Example: "AI Dashboard tracks engineering team AI adoption across the SDLC. Currently covering 
200+ engineers with usage analytics. Dashboard is functional; needs executive review of 
analytics approach and tech radar integration timeline."

## What the CTO Cares About

**Features Delivered:**
- [Feature 1]: [One-line business value]
- [Feature 2]: [One-line business value]
- [Feature 3]: [One-line business value]

**Adoption Metrics:**
- [Metric 1]: [Number] - [Context]
- [Metric 2]: [Number] - [Context]

**SDLC Coverage:**
- Dev phase: [Status/number]
- Review phase: [Status/number]
- Production: [Status/number]

## Technical Notes (For Reference Only)
*[Optional section - only include if specifically asked]*
- Authentication: [How login works]
- Performance: [Loading time / optimization]
- Data: [Storage approach]

## Analysis Approach
- **Primary lens**: Users first (engineer experience, not just tech metrics)
- **Separate views**: Analytics for leadership, Technology details for engineers
- **Omitted**: [What you deliberately left out and why]

## Decision Points for Leadership
1. [Question 1]: [Options] → [Recommendation]
2. [Question 2]: [Options] → [Recommendation]
3. [Question 3]: [Options] → [Recommendation]

## Next Steps
- Immediate: [Action]
- This week: [Action]
- Post-review: [Action]
```

**Key Pattern**: Lead with business value, keep technical details in optional section, 
frame everything through "what the CTO cares about" lens.

---

### 2. Technology Investment Justification

**Use when**: Asking for budget, headcount, or platform commitment

**Template Structure**:

```markdown
# Investment Proposal: [Technology/Initiative]

## The Business Problem
[Current state pain] costs us [quantified impact] per [time period].

Examples:
- "Manual database provisioning takes 2-3 weeks per request, blocking 15+ projects"
- "Legacy platform requires 40hrs/week DBA time, pulling engineers from product work"
- "Security compliance gaps create audit risk and potential regulatory exposure"

## Investment Thesis
**We are investing in [outcome], not [technology].**

| Investment | Business Outcome |
|-----------|------------------|
| Self-service platform | Reduce provisioning time from 3 weeks to 30 minutes |
| Automation tooling | Reallocate 40hrs/week DBA time to product engineering |
| Modern security stack | Eliminate compliance gaps and reduce audit preparation by 60% |

## The Win for Stakeholders

**Engineering Teams:**
- What they win: [Capability they gain]
- What they lose: [Very small - usually nothing]

**Security/Compliance:**
- What they win: [Risk reduction, audit readiness]
- What they lose: [Minimal]

**Finance:**
- What they win: [Cost avoidance, efficiency gains]
- Cost: [Investment required] with [payback period]

## Alternatives Considered

| Option | Investment | Outcome | Why Not Selected |
|--------|-----------|---------|------------------|
| Status Quo | $0 | Continue losing [X] per month | Unsustainable |
| [Option B] | [Cost] | [Outcome] | [Specific gap] |
| [Option C] | [Cost] | [Outcome] | [Specific gap] |

## Timeline & Milestones
- Month 1-2: [Phase with deliverable]
- Month 3-4: [Phase with deliverable]
- Month 5-6: [Phase with deliverable]
- Ongoing: [Operational state]

## Risk Mitigation
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|---------|------------|
| [Risk 1] | Medium | High | [Mitigation strategy] |
| [Risk 2] | Low | Medium | [Mitigation strategy] |

## Ask
- Budget: [Amount] for [time period]
- Headcount: [FTE] for [duration]
- Commitment: [What you need from leadership]

## What We're NOT Doing (Scope Boundaries)
- [Out of scope item 1]: [Why - usually "separate initiative" or "phase 2"]
- [Out of scope item 2]: [Why]
```

**Key Pattern**: Frame as business outcome investment, not technology adoption. 
Use "What they win" language, keep technical alternatives minimal.

---

### 3. The 5-Slide Leadership Presentation

**Use when**: Major initiative review, platform launch, strategic alignment meeting

**Slide Structure**:

**Slide 1: Why**
- Context: "[Area] is the last pillar to modernize"
- Urgency: [Forcing function or opportunity]
- Strategic fit: How this supports [broader strategy]

**Slide 2: Problems We Seek to Solve**
- Current state: [Pain point 1]
- Current state: [Pain point 2]
- Current state: [Pain point 3]
- *Keep to 3 max - executives can't absorb more*

**Slide 3: Achievements (Business Value)**
- Self-service: [What teams can now do independently]
- Automation: [What no longer requires manual intervention]
- Standardization: [Pattern consolidation benefit]
- *Focus on "what's in it for them"*

**Slide 4: How (Approach)**
- High-level approach: [Methodology/strategy]
- Key components: [3-4 bullet points, no jargon]
- Timeline: [Visual timeline with milestones]

**Slide 5: What You'll Need to Do**
- New [things]: [Effort required]
- Migration of [existing]: [Effort required]
- No action needed for: [What continues working]
- *Be explicit about asks - don't surprise them later*

**Speaking Notes Template**:
- "What's in it for you: [stakeholder-specific benefit]"
- "What you win: [specific capability or risk reduction]"
- "Small technical detail: [only if asked, otherwise omit]"

**Key Pattern**: Every slide answers "what's in it for them" and "what they win". 
Technical details are speaking notes only, not on slides.

---

### 4. Adoption & Progress Dashboard

**Use when**: Reporting metrics to leadership, showing initiative progress

**Template Structure**:

```markdown
# [Initiative] Dashboard: [Date]

## Executive Summary Bar
🎯 Target: [Goal] | 📊 Current: [Number/%] | ⏱️ Timeline: [Status]

## Adoption by Cohort
| Cohort | Adopted | In Progress | Not Started | Blockers |
|--------|---------|-------------|-------------|----------|
| [Team A] | [X%] | [Y%] | [Z%] | [If any] |
| [Team B] | [X%] | [Y%] | [Z%] | [If any] |
| [Team C] | [X%] | [Y%] | [Z%] | [If any] |

## Key Metrics

**Usage:**
- [Metric 1]: [Current] / [Target] ([Trend])
- [Metric 2]: [Current] / [Target] ([Trend])

**Outcomes:**
- [Business outcome 1]: [Quantified impact]
- [Business outcome 2]: [Quantified impact]

## Red Flags
| Issue | Severity | Owner | ETA |
|-------|----------|-------|-----|
| [Issue 1] | 🔴 High | [Name] | [Date] |
| [Issue 2] | 🟡 Medium | [Name] | [Date] |

## Success Stories
- [Team/Project]: [What they achieved with the tool/initiative]
- [Team/Project]: [Specific business impact]

## What Leadership Should Know
- [Insight 1]: [Strategic implication]
- [Insight 2]: [Decision needed or FYI]
```

**Key Pattern**: Lead with target/current/timeline bar, show cohort breakdown, 
flag issues explicitly, highlight business outcomes not just usage.

---

### 5. Vendor Assessment for Leadership

**Use when**: Evaluating SaaS, tools, or platforms for executive approval

**Template Structure**:

```markdown
# Vendor Assessment: [Vendor/Product]

## Executive Summary
**Recommendation**: [Approve / Reject / Conditional]
**Investment**: [Amount] for [period]
**Risk Level**: [Low/Medium/High] - [One-line rationale]

## Business Case

**Problem We Solve:**
[Current gap] costs us [impact] and creates [risk].

**Solution:**
[Vendor] provides [capability] that [outcome].

**Alternatives Considered:**
| Alternative | Gap | Why Not Selected |
|-------------|-----|------------------|
| Build in-house | [6-12 months, ongoing maintenance] | Time-to-value too slow |
| [Competitor] | [Specific capability gap] | [Specific limitation] |
| Status quo | [Continued pain/risk] | Unsustainable |

## Risk Assessment
| Risk | Likelihood | Business Impact | Mitigation |
|------|-----------|-------------------|------------|
| Vendor stability | Low | High | [Contract terms, data portability] |
| Integration complexity | Medium | Medium | [Phased rollout, fallback plan] |
| Adoption resistance | Medium | Low | [Training plan, champions program] |

## Total Cost of Ownership

**Year 1:** [License + Implementation + Training]
**Year 2-3:** [Ongoing license + support]
**Cost Avoidance:** [What we no longer need to spend on]

**Payback Period:** [X months] via [specific savings]

## What We're Getting

**Capabilities:**
- [Capability 1]: [Business value]
- [Capability 2]: [Business value]
- [Capability 3]: [Business value]

**Not Included (Out of Scope):**
- [Feature 1]: [Why not needed / phase 2]
- [Feature 2]: [Why not needed / phase 2]

## Implementation Approach
- Phase 1: [Pilot scope] - [Timeline]
- Phase 2: [Broader rollout] - [Timeline]
- Phase 3: [Full adoption] - [Timeline]

## Decision Required
- [ ] Approve [budget amount] for [period]
- [ ] Assign [resource] for [role]
- [ ] Commit to [timeline milestone]
```

**Key Pattern**: Lead with clear recommendation, frame as business problem solution, 
show total cost of ownership with payback, explicitly state what's NOT included.

---

### 6. Technical Risk → Business Risk Translation

**Use when**: Flagging technical debt, security issues, or architecture concerns to leadership

**Template Structure**:

```markdown
# Risk Alert: [Technical Area]

## The Business Risk
[Technical issue] creates [business impact].

**If this fails:**
- [Financial impact]: [Revenue loss / cost exposure]
- [Operational impact]: [Service disruption / customer impact]
- [Compliance impact]: [Regulatory exposure]
- [Reputational impact]: [Customer trust / brand damage]

**Current State:**
- Likelihood: [High/Medium/Low] based on [observed patterns]
- Time horizon: [Immediate / 6 months / 1 year]
- Trend: [Getting worse / Stable / Improving]

## What We're Doing About It
| Action | Owner | Timeline | Business Outcome |
|--------|-------|----------|------------------|
| [Action 1] | [Name] | [Date] | [Risk reduction] |
| [Action 2] | [Name] | [Date] | [Risk reduction] |
| [Action 3] | [Name] | [Date] | [Risk reduction] |

## Options & Recommendation

**Option A: [Aggressive fix]**
- Investment: [Cost/time]
- Outcome: [Risk elimination]
- Trade-off: [What we deprioritize]

**Option B: [Moderate fix]** - *Recommended*
- Investment: [Cost/time]
- Outcome: [Risk reduction to acceptable level]
- Trade-off: [What we accept]

**Option C: [Status quo]**
- Investment: $0
- Outcome: [Risk acceptance]
- Trade-off: [Continued exposure]

## Ask
- Approve [investment] for [approach]
- Accept risk for [duration] if Option B selected
- Assign [resource] as [role]
```

**Key Pattern**: Never lead with technical detail. Always start with business risk 
and financial/operational impact. Technical explanation is appendix only.

---

### 7. Architecture Decision Record (Executive Summary)

**Use when**: ADR needs leadership visibility or sign-off

**Template Structure**:

```markdown
# ADR Summary: [Decision Title]

## Decision
We will [what we're doing] for [scope/boundary].

## Why This Matters to Leadership
| Driver | Current State | Risk if We Don't Decide |
|--------|--------------|-------------------------|
| Strategy | [How this supports/refutes strategy] | [Strategic drift] |
| Security | [Current exposure] | [Breach/litigation risk] |
| Operations | [Current burden] | [Scaling failure] |
| Cost | [Current spend] | [Cost growth] |

## What We Evaluated
| Option | Investment | Timeline | Business Outcome |
|--------|-----------|----------|------------------|
| [Option A] | [Cost] | [Duration] | [Outcome] |
| [Option B] | [Cost] | [Duration] | [Outcome] - Selected |
| [Option C] | [Cost] | [Duration] | [Outcome] |

## What We're NOT Doing
- [Rejected option]: [Why - usually cost, timeline, or strategic fit]
- [Scope limitation]: [Why - phase 2 or separate initiative]

## Impact on Teams
| Stakeholder | What Changes | Support Provided |
|-------------|-------------|------------------|
| [Team A] | [Impact] | [Training/docs] |
| [Team B] | [Impact] | [Migration assistance] |

## Timeline & Checkpoints
- [Date]: [Milestone with validation]
- [Date]: [Milestone with validation]
- [Date]: [Final outcome validation]

## Decision Required
- [ ] Approve [approach]
- [ ] Accept [specific risk/trade-off]
- [ ] Assign [resource] for [role]
```

**Key Pattern**: Executive ADR compresses technical detail into "Why This Matters" 
table, focuses on stakeholder impact and business outcomes, keeps timeline visible.

---

## What You Deliberately Omit

Based on your patterns, you consistently leave out:

### Always Omit from Executive Communications:
- **Implementation details**: Code structure, API specifics, data schemas
- **Technical dependencies**: Service meshes, specific library versions
- **Process minutiae**: Sprint velocity, PR review times (unless specifically asked)
- **Acronyms without definition**: Assume minimal technical context
- **Debugging details**: Error logs, stack traces, root cause analysis

### Omit Unless Specifically Asked:
- **Architecture diagrams**: Include only if leadership asks for visualization
- **Tool comparisons**: Detailed feature matrices (keep to 2-3 bullets)
- **Migration specifics**: Step-by-step technical procedures
- **Performance metrics**: Latency, throughput, cache hit rates (unless business-relevant)

### Include Only in Appendix:
- **Security details**: Specific CVEs, patch versions
- **Compliance specifics**: Control mappings, audit procedures
- **Technical alternatives**: Detailed trade-off analysis

### Financial Services Stakeholder Considerations
When communicating in a regulated financial services environment:
- **Compliance officers** need to know: Does this change our control environment? Do we need to update our SOX narrative?
- **Legal/regulatory** needs to know: Does this affect any state lending licenses? Any customer data handling changes?
- **Auditors** (internal and external) need to know: Can they still get the evidence they need? Has the audit trail changed?
- **PE sponsors** need to know: Is the tech investment on track? Are we hitting cost reduction targets? Any compliance risks?

**Never surprise compliance or legal.** If a technical decision has regulatory implications, they hear about it before the CEO does.

---

## Your Communication Anti-Patterns

**Patterns to avoid (you've learned from these):**

1. **Too much technical detail upfront**
   - *Mistake*: Leading with architecture diagrams
   - *Correction*: Lead with business outcome, add diagrams as appendix

2. **Assuming technical context**
   - *Mistake*: Using jargon without explanation
   - *Correction*: Define terms or replace with business language

3. **Feature-focused rather than outcome-focused**
   - *Mistake*: "We built X dashboard with Y features"
   - *Correction*: "Engineers can now self-serve database provisioning in 30 minutes"

4. **Hiding trade-offs**
   - *Mistake*: Presenting only recommended option
   - *Correction*: Always show 2-3 options with explicit rejection rationale

5. **Surprise asks at the end**
   - *Mistake*: Business case with ask buried in final slide
   - *Correction*: Lead with ask, support with business case

---

## Cross-Skill Integration Map

This skill is the **presentation layer** for all other skills. Every skill produces outputs that may need executive framing.

### Input → Template Mapping
| Source Skill | Output Type | Use This Template |
|---|---|---|
| **architecture-assessor** | 90-day assessment report | Executive Summary + maturity scores |
| **architecture-assessor** | Critical risk findings | Risk Translation template |
| **architecture-assessor** | Vendor portfolio analysis | Vendor Assessment template |
| **decision-engine** | ADR requiring budget approval | Investment Justification + Executive ADR |
| **decision-engine** | Build vs buy decision | Investment Justification template |
| **vendor-evaluator** | Vendor recommendation memo | Vendor Assessment template |
| **vendor-evaluator** | Vendor consolidation plan | Cost Rationalization Narrative |
| **terraform-module-scaffold** | Infrastructure cost metadata | Cost Rationalization Narrative |
| **runbook-generator** | Operational maturity evidence | Adoption Dashboard template |
| **migration-playbook** | Migration scope document | Investment Justification (phase-gated) |
| **migration-playbook** | Phase completion report | Adoption Dashboard + Cost Rationalization Narrative |
| **migration-playbook** | Migration completion + decommission | Cost Rationalization Narrative (savings realized) |

### Presentation Cadence for First 90 Days
| Week | Deliverable | Template | Audience |
|------|------------|----------|----------|
| 2 | Initial findings briefing | Executive Summary | CEO + CTO |
| 4 | Architecture assessment results | Executive Summary + Risk Translation | Leadership team |
| 6 | Quick wins progress | Adoption Dashboard | CEO + CTO |
| 8 | Vendor rationalization plan | Cost Rationalization Narrative | CEO + CFO + PE sponsor |
| 10 | First ADR for major decision | Executive ADR + Investment Justification | Leadership team |
| 12 | 90-day report | 5-Slide Presentation | Board/PE sponsor |

---

## Quick Reference: Which Template to Use

| Situation | Template | Key Pattern |
|-----------|----------|-------------|
| Tool built, needs CTO review | Executive Summary | What CTO cares about + decision points |
| Asking for budget/headcount | Investment Justification | Investment thesis + stakeholder wins |
| Initiative review presentation | 5-Slide Deck | Why → Problems → Achievements → How → Ask |
| Reporting metrics monthly | Adoption Dashboard | Target/current/timeline + red flags |
| Evaluating vendor/platform | Vendor Assessment | Risk + TCO + what's NOT included |
| Flagging technical debt | Risk Translation | Business risk first, technical details last |
| ADR needs leadership eyes | Executive ADR | Strategy alignment + stakeholder impact |

---

## Usage Workflow

### Before Writing:
1. **Identify the ask**: What do you need from leadership?
2. **Choose template**: Match situation type to template
3. **Gather metrics**: Quantify business impact (not technical metrics)
4. **Frame options**: Prepare 2-3 alternatives with rejection rationale

### While Writing:
1. **Lead with outcome**: Business value in first paragraph
2. **Use stakeholder language**: "What they win" not "what we built"
3. **Flag red flags early**: Don't bury bad news
4. **Be explicit about asks**: Clear decision points at the end

### After Writing:
1. **Strip technical detail**: Move to appendix or delete
2. **Check jargon**: Replace with business language
3. **Validate metrics**: Can leadership act on these numbers?
4. **Review asks**: Is what you need crystal clear?

---

## For Your Team

Share this playbook with:

> "Use these templates for any communication to leadership. They ensure we:
> - Lead with business value, not technical detail
> - Show 2-3 options with explicit trade-offs
> - Flag risks and red flags early
> - Make asks clear and decision-ready
> 
> The goal: leadership gets what they need in 5 minutes or less."

Update templates as your patterns evolve.
