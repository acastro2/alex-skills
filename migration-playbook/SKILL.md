---
name: migration-playbook
description: "Plan and execute system migrations, platform modernizations, database cutovers, service decompositions, library swaps, and infrastructure transitions using a repeatable phased methodology with validation gates, rollback triggers, and stakeholder communication cadence. Use when planning a migration, sequencing a rollout, managing a cutover, building a transition plan, modernizing a platform, swapping a library or provider, decomposing a monolith, or when someone asks 'how do we get from here to there'. Produces phase-gated migration plans with dependency maps, rollback criteria, validation checkpoints, and executive-ready progress reporting tied to cost, risk, and business continuity."
---

# Migration Playbook

Your documented migration patterns extracted from 90+ migration sessions across database modernization, infrastructure transitions, tool adoptions, library swaps, and platform rollouts.

---

## When to Use

- Planning a migration of any scope (database, service, platform, library, provider)
- Sequencing a multi-step rollout or modernization initiative
- Managing a cutover or transition between old and new systems
- Building backward compatibility or parallel-run strategies
- Coordinating cross-team infrastructure changes
- Creating migration tickets, scope documents, or project plans
- Presenting migration plans to leadership for approval

---

## PE-Backed Financial Services Migration Context

### The Fundamental Constraint
In a PE-backed consumer lender, technology is viewed as a cost center. Every migration plan must answer: **"Why should we spend money changing something that already works?"**

### Migration Investment Framing
Never present migrations as technical improvement. Frame as:

1. **Risk elimination** — "This system has X known failure modes that cost $Y per incident"
2. **Cost reduction** — "Current annual run-rate is $X; post-migration is $Y (Z% reduction)"
3. **Regulatory compliance** — "Current state creates audit findings; migration resolves them"
4. **Revenue enablement** — "Migration unblocks capability X which drives $Y in revenue"
5. **Operational efficiency** — "Current process requires X person-hours; post-migration requires Y"

### Phase-Gated Investment Pattern
PE sponsors reject big-bang budget requests. Structure every migration as:

| Phase | Investment | Deliverable | Business Value |
|-------|-----------|-------------|----------------|
| Assessment | Low (1-2 weeks) | Scope document + risk map | Clear picture of cost/risk |
| Foundation | Medium (2-4 weeks) | Tooling + staging validation | Proven approach, de-risked |
| Migration | Medium-High (varies) | Phased cutover | Incremental risk reduction |
| Validation | Low (1-2 weeks) | Verification + decommission | Cost savings realized |

> **Rule**: Every phase produces a deliverable that has standalone value even if the next phase is delayed or cancelled.

### Regulatory Constraints on Migrations
- **SOX systems**: Change management approval required before every production migration step
- **PCI-DSS scope**: Data-handling systems require security review of migration tooling
- **State lending data**: Data residency requirements constrain where migration staging can occur
- **Audit trail**: Every migration step must produce evidence (who, what, when, approval)
- **Business continuity**: Zero revenue disruption is a constraint, not a goal — build maintenance windows into the plan

---

## Universal Migration Template

Every migration, regardless of type, follows this structure:

### Phase 0: Scope & Inventory

**Your pattern**: Start with a full inventory, then aggressively scope down.

```markdown
## Migration Scope Document

### Vision
[One sentence: "what does the world look like when this is done?"]
Example: "Factory-built automation replacing handcrafted operations"

### Objectives (max 5, terse)
1. [Business outcome, not technical activity]
2. ...

### Full Inventory
| Item | Category | Status | Migration Complexity | Priority |
|------|----------|--------|---------------------|----------|
| ... | Critical / High / Medium / Low | Active / Deprecated / Unknown | Simple / Moderate / Complex | P0 / P1 / P2 |

### Scope Boundaries
**IN SCOPE:**
- [Explicit list of what IS being migrated]

**OUT OF SCOPE:**
- [Explicit list of what is NOT being migrated and WHY]
- [Things that look like they should be in scope but aren't]

**DEFERRED:**
- [Items pushed to a future phase with rationale]

### Known Constraints
- [Resource constraints: team availability, skill gaps]
- [Technical constraints: dependencies, compatibility]
- [Business constraints: maintenance windows, freeze periods]
- [Regulatory constraints: approvals, audit requirements]

### Assumptions (with validation plan)
- [ ] [Assumption 1] — validate by [date/method]
- [ ] [Assumption 2] — validate by [date/method]

### Disclaimer
> This scope represents [X]% analysis. Team expertise validates 
> and completes the remaining [Y]%. This is a starting point for 
> collaborative refinement, not a final mandate.
```

**Why the disclaimer matters**: You consistently used an "80% analysis" pattern — acknowledging that the migration planner never has complete knowledge. The teams closest to the systems fill the gaps. This builds buy-in instead of resistance.

### Phase 1: Foundation

**Your pattern**: Build shared tooling and abstractions BEFORE migrating any individual component.

- Create shared connection libraries, configuration templates, or automation modules first
- Validate the migration toolchain in a non-production environment
- Prove the approach works on 1-2 low-risk items before scaling

**Foundation Checklist:**
- [ ] Migration tooling selected and validated
- [ ] Shared libraries/abstractions built (connection strings, configs, auth)
- [ ] Non-production environment mirrors production topology
- [ ] First migration executed successfully in staging
- [ ] Rollback procedure tested in staging
- [ ] Monitoring/alerting configured for migration metrics
- [ ] Runbook drafted for migration execution (see `runbook-generator`)
- [ ] Team walkthrough completed — everyone understands the process

**Gate criteria to proceed**: Foundation tooling works in staging. At least one low-risk item migrated and validated end-to-end. Rollback tested.

### Phase 2: Critical Path

**Your pattern**: Migrate the highest-risk, highest-value items next — not last.

- Critical items go second (after foundation), not at the end when fatigue sets in
- Group items by dependency, not by perceived difficulty
- Batch where possible — migrate related items together, not one at a time

**Dependency Ordering Logic:**
1. Map dependencies between migration items (what must move before what?)
2. Identify shared resources (databases, APIs, configs) that multiple items depend on
3. Migrate shared resources FIRST
4. Migrate consumers in dependency order
5. Items with no dependencies can be parallelized

**Validation Checkpoints (per batch):**
- [ ] Pre-migration: Baseline metrics captured (latency, error rate, throughput)
- [ ] Migration executed per runbook
- [ ] Post-migration: Functional verification (key user flows work)
- [ ] Post-migration: Performance verification (metrics within 2x baseline)
- [ ] Post-migration: Integration verification (upstream/downstream systems healthy)
- [ ] Rollback window: Hold for [X hours/days] before decommissioning old system

### Phase 3: Remaining Items

**Your pattern**: Once the pattern is proven, scale it across remaining items with less ceremony.

- High and medium priority items follow the proven pattern
- Reduce per-item ceremony — batch approvals, standardized runbooks
- Track migration velocity to forecast completion date
- Flag any items that deviate from the pattern for individual attention

### Phase 4: Validation & Decommission

**Your pattern**: Old systems stay available for a defined retention period, then get decommissioned with evidence.

- Define retention period upfront (e.g., 30 days)
- Monitor old system for unexpected traffic during retention
- Decommission with a checklist, not a hope:

**Decommission Checklist:**
- [ ] No traffic to old system for [retention period]
- [ ] DNS/routing fully cut over
- [ ] Old system backups retained per compliance requirements
- [ ] Cost savings from decommission confirmed (instances stopped, licenses released)
- [ ] Decommission documented in change management system
- [ ] Stakeholders notified of decommission completion

### Phase 5: Handover

**Your pattern**: Explicit handover to operations with documentation and knowledge transfer.

- Migration docs become operational docs
- Team that runs the system validates they can operate it
- On-call runbooks updated
- Monitoring dashboards transitioned

---

## Migration Archetypes

### Archetype 1: Database Migration (Schema, Platform, Version)

**Extracted from**: Database modernization sessions (bare-metal → VM-based PostgreSQL, multi-phase production cutover)

**What's unique:**
- **Maintenance windows are non-negotiable** — databases require coordinated downtime (30-125 minutes per database in your sessions)
- **Replication validation is the critical gate** — never cut over until replication lag is zero and has been stable
- **30-day retention pattern** — keep old database accessible for 30 days post-cutover
- **Batch cutover approval** — migrate databases in batches, get single approval per batch (not per database)
- **Cross-team coordination** — DBA team, data engineering, application teams all have different concerns

**Sequencing:**
1. Staging databases first (prove the process)
2. Non-critical production databases (build confidence)
3. Critical production databases (batch cutover with approval)
4. Decommission old infrastructure

**Risk Profile:**
- **Highest risk**: Data loss or corruption during cutover
- **Mitigation**: Replication-based migration (not dump/restore), validated with checksums
- **Rollback trigger**: Replication lag > threshold, application errors > baseline, any data integrity check failure

**Rollback Approach:**
- Point DNS back to old database
- Old database remains read-write capable for full retention period
- Application connection strings use abstracted endpoints (DNS), not direct IPs

**Key Metrics:**
| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| Provisioning time | [X weeks] | [Y minutes] | Time from request to ready |
| Failover time | [manual, X hours] | [automated, <Y min] | Time to promote replica |
| Maintenance window | [X hours] | [Y minutes] | Per-database cutover |

### Archetype 2: Infrastructure Migration (On-Prem ↔ Cloud, Provider Swap)

**Extracted from**: VMware clone operations, infrastructure modernization, Terraform module work

**What's unique:**
- **Parallel operation is mandatory** — old and new infrastructure run simultaneously during transition
- **Network is the last thing to cut** — DNS and routing changes are the point of no return
- **Terraform state management** — import existing resources before modifying them
- **Provider abstraction** — build modules that work across providers (vSphere, baremetal, cloud)

**Sequencing:**
1. Build new infrastructure in parallel (no impact to existing)
2. Deploy application to new infrastructure (shadow mode)
3. Validate with synthetic traffic or shadow traffic
4. Gradual traffic shift (canary → percentage → full)
5. DNS cutover
6. Retention period on old infrastructure
7. Decommission

**Risk Profile:**
- **Highest risk**: Network partitions during cutover, state drift between environments
- **Mitigation**: Infrastructure-as-code for reproducibility, DNS-based routing for instant rollback
- **Rollback trigger**: Any customer-facing error rate increase, latency p95 > 2x baseline

### Archetype 3: Library/Component Swap

**Extracted from**: JWKS library replacement, SDK version upgrades, dependency modernization

**What's unique:**
- **TDD-driven replacement** — write tests proving current behavior, then swap implementation behind them
- **Four-task sequencing**: Prove compatibility → Replace implementation → Preserve behavior → Clean up dead code
- **Explicit "don't change" constraints** — define what must NOT change during the swap
- **Each task has its own verify cycle**: Write failing test → Verify it fails → Implement → Verify it passes

**Sequencing:**
1. Write characterization tests for current behavior
2. Verify tests pass with old implementation
3. Swap to new implementation
4. Verify ALL tests still pass (zero behavior change)
5. Remove old implementation and dead code
6. Final test run

**Risk Profile:**
- **Highest risk**: Subtle behavior differences between old and new implementation
- **Mitigation**: Comprehensive characterization tests, shadow/comparison mode if possible
- **Rollback trigger**: Any test failure, any behavior difference in production

### Archetype 4: Tool/Platform Adoption

**Extracted from**: Backstage adoption, tech radar migration, monitoring platform rollout

**What's unique:**
- **Incremental exposure** — don't launch to everyone at once
- **Hybrid adoption pattern** — selectively adopt platform components rather than wholesale adoption
- **Migration sequence**: Core functionality → Expose endpoints → Integrate consumers → Migrate content → Full adoption

**Sequencing:**
1. Core platform deployed (internal team only)
2. First consumer integration (single team, pilot)
3. Documentation and self-service guides
4. Phased team onboarding (2-3 teams per sprint)
5. Legacy tool deprecation notice
6. Migration support period
7. Legacy tool decommission

**Risk Profile:**
- **Highest risk**: Low adoption, shadow IT (teams keep using old tool)
- **Mitigation**: Make new tool demonstrably better for at least one workflow before mandating
- **Rollback trigger**: N/A — adoption is incremental, rollback = slow down adoption pace

### Archetype 5: Service Modernization (Monolith Decomposition, Frontend Rebuild)

**Extracted from**: Service migration sessions, frontend swap planning, MongoDB → PostgreSQL ADR

**What's unique:**
- **ADR-driven decisions** — every decomposition decision gets a decision record (see `decision-engine`)
- **Strangler fig pattern** — new service handles new requests, old service handles existing
- **Data migration is separate from service migration** — don't do both at once
- **API compatibility layer** — old consumers work against new service without changes

**Sequencing:**
1. Define service boundaries (which functionality moves where)
2. Build new service with API compatibility layer
3. Migrate data (separate workstream, see Archetype 1)
4. Route new traffic to new service
5. Gradually migrate existing traffic
6. Validate and decommission old service paths

**Risk Profile:**
- **Highest risk**: Distributed system failures, data consistency between old and new
- **Mitigation**: Feature flags per route, per-request routing, comprehensive integration tests
- **Rollback trigger**: Data inconsistency, error rate increase, feature regression

---

## Scope Management Pattern

**Your pattern**: Categorize everything, eliminate most, focus on what matters.

### The Elimination Funnel

From your DBA migration analysis — you started with ~200 items and narrowed to 120-150:

```
Full Inventory (~200 items)
    ↓ Remove deprecated/unused (−30-40%)
    ↓ Remove out-of-scope (−10-20%)
    ↓ Defer to future phase (−10%)
Active Migration Scope (~120-150 items)
    ↓ Categorize by priority
    Critical (~40%): Must migrate, business-critical
    High (~25%): Should migrate, operational value
    Medium (~20%): Migrate if time permits
    Low (~15%): Migrate last or defer
```

### Common Change Patterns
When migrating many components, identify the repeatable changes:

| Change Type | Example | Approach |
|-------------|---------|----------|
| Auth/credential swap | Hardcoded creds → Vault | Shared library, apply everywhere |
| Connection string update | Static → DNS-based | Config template, bulk update |
| API endpoint change | Old URL → New URL | Reverse proxy during transition |
| Framework upgrade | SDK v1 → v2 | Characterization tests + swap |

> **Pattern**: Build the shared solution for the most common change first. The 3-4 most common changes cover 70%+ of migration work.

---

## Rollback Strategy Framework

### Rollback Tiers

| Tier | Trigger | Action | Time to Recover |
|------|---------|--------|-----------------|
| **Instant** | Error rate spike during cutover | Revert DNS/routing | < 5 minutes |
| **Fast** | Performance degradation post-cutover | Redirect traffic to old system | < 30 minutes |
| **Planned** | Functional issues found in retention period | Coordinate rollback with teams | < 4 hours |
| **Emergency** | Data integrity issue | Stop all traffic, assess, restore from backup | Varies |

### Abort Criteria
Define these BEFORE starting migration, not during:

- **Hard abort**: Any data loss or corruption → immediate rollback, incident declared
- **Soft abort**: Error rate > 2x baseline for > 5 minutes → pause and assess
- **Slow abort**: Performance degradation > 50% for > 15 minutes → begin rollback
- **Business abort**: Any impact to revenue-generating transactions → immediate rollback

### Parallel Operation Rules
- Old system stays fully operational during migration (read AND write capable)
- New system validated before any traffic shift
- Both systems monitored simultaneously with comparative dashboards
- Cutover is the LAST step, not the first

---

## Communication Pattern

### Stakeholder Communication Cadence

**Your pattern from cutover sessions**: Phase-based, team-specific, approval-gated.

| Phase | Audience | Format | Cadence |
|-------|----------|--------|---------|
| Scope & Planning | Leadership + technical leads | Scope document review | Once |
| Foundation | Technical teams | Status email/Slack | Weekly |
| Pre-cutover | All stakeholders | Cutover plan + approval request | Once per batch |
| During cutover | Operations team | Real-time Slack channel | Continuous |
| Post-cutover | Leadership | Summary with metrics | Within 24h |
| Decommission | All stakeholders | Notification | Once |

### Team-Specific Messaging

**Your pattern**: Different teams get different messages about the same migration.

| Audience | They Care About | Your Message Focuses On |
|----------|----------------|------------------------|
| Leadership/PE | Cost, risk, timeline | Investment phases, ROI projections, risk reduction |
| Application teams | "Will my app break?" | Maintenance windows, what they need to change, support |
| DBA/Operations | Technical details | Runbooks, rollback procedures, monitoring changes |
| Data Engineering | Data pipeline impact | Replication changes, CDC updates, connection strings |
| Security/Compliance | Audit trail, controls | Change management compliance, evidence collection |

### Batch Approval Pattern
Don't ask for approval one item at a time. Group related items:

```markdown
## Phase 2 Batch Cutover — Approval Request

### Summary
Requesting approval to migrate [X] databases in [Y] maintenance 
windows over [Z] weeks.

### Batch Contents
| Item | Risk Level | Maintenance Window | Rollback Time |
|------|-----------|-------------------|---------------|
| ... | Low/Med/High | Date + duration | X minutes |

### Prerequisites Completed
- [ ] All items validated in staging
- [ ] Runbooks reviewed and approved
- [ ] Rollback procedures tested
- [ ] Monitoring configured
- [ ] On-call team briefed

### Approval
- [ ] Technical lead approval: __________ Date: __________
- [ ] Operations approval: __________ Date: __________
- [ ] Change management approval: __________ Date: __________
```

---

## Timeline Estimation Pattern

### Phase-Based Estimation

**Your pattern**: Estimate by phase, not by item. Buffer at phase boundaries.

| Phase | Typical Duration | Buffer | Dependencies |
|-------|-----------------|--------|-------------|
| Assessment/Scope | 1-2 weeks | None | Access to systems and teams |
| Foundation | 2-4 weeks | +1 week | Tooling decisions, environment setup |
| Critical Path | 2-6 weeks | +2 weeks | Team availability, maintenance windows |
| Remaining Items | 2-8 weeks | +2 weeks | Velocity from critical path |
| Validation | 1-2 weeks | +1 week | Retention period |
| Handover | 0.5-1 week | None | Documentation complete |

### Velocity-Based Forecasting
After completing Phase 2 (Critical Path), use actual migration velocity to forecast Phases 3-4:

```
Items remaining: X
Average items per week (from Phase 2): Y
Estimated weeks remaining: X/Y + buffer
```

### Duration Estimation for Maintenance Windows
From your database sessions — per-item cutover windows:

| Migration Type | Window Size | Risk Level |
|---------------|-------------|------------|
| Small database (< 50GB) | 30-60 minutes | Low |
| Medium database (50-500GB) | 60-120 minutes | Medium |
| Large database (> 500GB) | 2-4 hours | High |
| Infrastructure cutover | 30-60 minutes | Medium |
| DNS change propagation | 15-30 minutes | Low |
| Library swap (with tests) | 0 (deploy pipeline) | Low |

---

## Migration Ticket Structure

### Your Pattern: Epic → Spike → Setup → Migration

From your Jira ticket creation sessions:

```
Epic: [Migration Name] Modernization
├── Spike: Assessment & scope (1-2 weeks)
├── Setup: Foundation & tooling (per-environment)
│   ├── Setup: Staging environment preparation
│   └── Setup: Production environment preparation
└── Migration: Per-batch execution
    ├── Migration: Batch 1 — [Items] (staging)
    ├── Migration: Batch 1 — [Items] (production)
    ├── Migration: Batch 2 — [Items] (staging)
    ├── Migration: Batch 2 — [Items] (production)
    └── ...
```

**Ticket Template (per migration batch):**

```markdown
## Summary
Migrate [items] from [old] to [new] in [environment].

## Acceptance Criteria
- [ ] Items migrated per runbook
- [ ] Validation checkpoints passed
- [ ] Monitoring confirms healthy operation
- [ ] Rollback not triggered within retention period
- [ ] Documentation updated

## Dependencies
- Blocked by: [Setup tickets, prior batches]
- Blocks: [Next batches, decommission]

## Runbook Reference
[Link to runbook-generator output]

## Rollback Plan
[Link to rollback section of runbook]

## Compliance
- Change management ticket: [ID]
- Approval status: [Pending/Approved]
- Audit evidence location: [Path]
```

---

## Anti-Patterns

### Things You Explicitly Avoid

1. **Big-bang migration** — Never migrate everything at once. Phase it. Validate each phase. Get approval per phase. Even if someone says "just do it all this weekend."

2. **Mixing migration types** — Don't change schema AND platform AND tooling in one phase. Separate concerns. Schema migration is separate from platform migration is separate from tooling migration.

3. **Starting without shared libraries** — Don't let each team build their own migration tooling. Build the shared connection library / config template / automation module FIRST, then distribute.

4. **Ignoring cross-system dependencies** — Always check what ELSE touches the same resource. Two repos managing the same database. Three services sharing a connection pool. This is where migrations break.

5. **Underestimating scope** — Do the full inventory. Even if it seems like overkill. Your 200 → 150 pattern exists because the first estimate is always low. Count everything, then eliminate.

6. **Skipping staging validation** — "It worked in dev" is not validation. Every migration runs in staging first, with the same runbook, same tooling, same team. Staging is the dress rehearsal.

7. **Permanent parallel operation** — Parallel systems must have a defined end date. Running two systems indefinitely doubles cost and complexity. Set the retention period on day 1 and enforce it.

8. **Hero migrations** — One person who knows the system running the migration solo. Runbooks exist so ANY qualified operator can execute. If only one person can run it, the runbook isn't done.

9. **Post-hoc scope documents** — Writing the scope document after starting migration. Scope FIRST. Always. Even a rough one. Refine it, but start with boundaries.

10. **Optimistic timelines without buffers** — Your phase buffers exist because migrations surface surprises. The buffer is not padding — it's recognition that you can't know everything upfront (see the 80% disclaimer).

---

## Cross-Skill Integration

### Inputs From Other Skills

| Trigger | Source Skill | What It Provides |
|---------|-------------|-----------------|
| Assessment finds migration-worthy system | `architecture-assessor` | Risk profile, current state, priority |
| Decision made to migrate (not build new) | `decision-engine` | ADR with rationale, constraints, approach |
| Vendor selected for target platform | `vendor-evaluator` | Vendor capabilities, integration requirements |

### Outputs To Other Skills

| Output | Destination Skill | How It's Used |
|--------|------------------|---------------|
| Migration scope document | `executive-framer` | Investment justification, board update |
| Migration runbook | `runbook-generator` | Operational execution procedures |
| Migration infrastructure | `terraform-module-scaffold` | IaC for new environment |
| Phase completion report | `executive-framer` | Progress reporting to leadership |
| Migration ADR (when needed) | `decision-engine` | Document approach decisions |

### Migration → Executive Presentation Flow
Every migration phase produces an executive-ready artifact:

1. **Assessment complete** → Executive Summary (via `executive-framer`)
2. **Foundation complete** → Investment Justification with proven approach
3. **Each batch complete** → Progress dashboard with metrics
4. **Migration complete** → Cost savings realization report
5. **Decommission complete** → Final savings + lessons learned

---

## Quick Reference: Migration Decision Matrix

| Situation | Start Here | Key Question |
|-----------|-----------|--------------|
| "We need to migrate database X" | Archetype 1 + Phase 0 scope | What's the maintenance window? |
| "We're moving to cloud" | Archetype 2 + Phase 0 inventory | What runs in parallel during transition? |
| "Swap library X for library Y" | Archetype 3 + characterization tests | Do we have tests proving current behavior? |
| "Roll out new tool to all teams" | Archetype 4 + pilot plan | Which team goes first and why? |
| "Rebuild the frontend" | Archetype 5 + strangler fig | Can old and new coexist behind a router? |
| "Modernize the platform" | Phase 0 full scope, then sequence archetypes | What's the dependency order across systems? |

---

## The 80% Pattern

Your most distinctive migration pattern: **Acknowledge what you don't know.**

Every scope document, every timeline, every risk assessment includes a version of:

> "This represents ~80% of the analysis. The remaining 20% requires 
> team expertise and hands-on validation. This is a starting point 
> for collaborative refinement — not a mandate to be executed blindly."

This isn't hedging. It's a deliberate strategy:
- **Builds buy-in** — teams feel ownership, not mandate
- **Catches blind spots** — the team closest to the system knows what you missed
- **Prevents failure** — better to plan for gaps than to pretend they don't exist
- **Sets expectations** — leadership knows the plan will evolve

Use this pattern in every migration scope document, every timeline estimate, every risk assessment. The teams that execute the migration should improve the plan, not just follow it.
