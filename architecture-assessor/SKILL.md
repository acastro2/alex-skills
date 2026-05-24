---
name: architecture-assessor
description: "Assess and evaluate system architecture, infrastructure health, and technical maturity across domains. Use when asked to assess a stack, evaluate a system, review architecture, perform due diligence, audit technical capabilities, determine what to look at first, or score infrastructure maturity. Produces actionable health reports with prioritized findings tied to cost, risk, and regulatory impact."
---

# Architecture Assessor

A portable assessment toolkit for evaluating technical systems across domains. This skill helps identify architectural patterns, anti-patterns, gaps, and risks in any codebase or infrastructure.

## When to Use

- Evaluating a system you're inheriting or considering acquiring
- Conducting technical due diligence
- Building architecture assessment capabilities for a VP/Principal role
- Identifying blind spots in your own assessment patterns
- Creating consistent evaluation frameworks across teams

## PE-Backed Financial Services Context

At a PE-backed consumer lender, every assessment finding must connect to one of three pillars:
- **Cost**: What does this system cost to operate? Is there waste, duplication, or consolidation opportunity?
- **Risk**: What regulatory, operational, or security risk does this expose? SOX, PCI-DSS, state lending regulations, GLBA?
- **Revenue**: Does this system protect or enable revenue? What's the blast radius if it fails?

### Financial Services Assessment Priorities
When assessing a consumer lending technology stack, prioritize in this order:
1. **Regulatory compliance posture** - Can we pass an audit tomorrow?
2. **Data security and privacy** - Consumer financial data (GLBA, state privacy laws, PCI-DSS for payment data)
3. **System reliability** - Loan origination, payment processing, collections cannot go down
4. **Cost structure** - PE shops expect 15-30% infrastructure cost reduction in first 18 months
5. **Technical debt velocity** - Is debt accumulating faster than the team can pay it down?
6. **Vendor concentration risk** - Single points of failure in the vendor portfolio

## Assessment Framework

### Domain Coverage & Blind Spots

Based on assessment history analysis:

**Strong Coverage (10+ patterns each):**
- AI/ML Ops & Developer Platforms
- Infrastructure as Code (Terraform)
- Configuration Management (Ansible)
- Observability (extrapolated from Datadog modules)
- Security & Identity (extrapolated from Vault/LDAP work)

**Moderate Coverage (5-10 patterns):**
- Data Infrastructure
- Documentation & Knowledge Systems
- CI/CD (extrapolated from pipeline work)
- Event Streaming (extrapolated from Kafka work)

**Weak Coverage (3-5 patterns) - Conscious Blind Spots:**
- Developer Experience (Backstage, portals)

**Assessment Methodology Notes:**
- *Direct patterns:* Extracted from 1109 assessment-focused sessions across 73 projects
- *Extrapolated patterns:* Derived from your infrastructure implementations and cross-domain reasoning
- *ADD FROM EXPERIENCE markers:* Areas where your deep expertise exceeds what's captured in session titles

### Assessment Checklist by Domain

#### AI/ML Ops & Developer Platforms

**FIRST-LEVEL CHECKS (Initial Assessment)**

**Check: Tool Configuration Validation**
- What to verify: LLM provider configs, API keys, rate limiting, fallback mechanisms
- Why it matters: Misconfigured AI tools fail silently or produce degraded outputs without obvious errors
- Red flag: No retry logic, missing provider fallbacks, hardcoded credentials

**Check: Data Flow & Insertion Patterns**
- What to verify: Data lineage from ingestion to storage, validation at boundaries, idempotency
- Why it matters: AI systems are data-hungry; broken pipelines corrupt models and decisions
- Red flag: Missing input validation, no deduplication, silent data loss

**Check: Context Window & Token Management**
- What to verify: Token counting implementation, truncation strategies, prompt caching
- Why it matters: Exceeding limits causes failures; poor management wastes 50%+ of API spend
- Red flag: No token tracking, unbounded inputs, missing truncation logic

**Check: Authentication/Authorization Flows**
- What to verify: Service-to-service auth, user permission propagation, audit trails
- Why it matters: AI systems often access sensitive data; weak controls create compliance risks
- Red flag: No auth on internal APIs, missing audit logs, overly broad permissions

**DEEPER-DIVE CHECKS (Detailed Analysis)**

**Check: Spec Document Completeness**
- What to verify: Acceptance criteria, edge cases, error scenarios, rollback procedures
- Why it matters: AI specs often focus on happy path; reality is messy
- Red flag: Missing error handling, no rollback plan, undefined edge cases

**Check: Codebase Exploration Systematics**
- What to verify: Consistent exploration patterns, documentation cross-references, hidden dependencies
- Why it matters: AI-enhanced codebases have complex tool chains that are hard to trace
- Red flag: Undocumented tool dependencies, missing context references, hallucinated docs

**Check: UI Data Accuracy & Rendering**
- What to verify: Data freshness indicators, tooltip accuracy, error state handling
- Why it matters: AI dashboards lose trust fast when numbers don't match reality
- Red flag: Stale data without warnings, misleading tooltips, missing error states

---

#### Infrastructure as Code (Terraform)

**FIRST-LEVEL CHECKS**

**Check: Module Structure Consistency**
- What to verify: Input/output contracts, versioning strategy, documentation completeness
- Why it matters: Inconsistent modules create "works on my machine" infrastructure
- Red flag: Missing READMEs, undocumented inputs, no version constraints

**Check: Variable Usage Patterns**
- What to verify: Local vs. global scope, default values, validation rules
- Why it matters: Poor variable hygiene spreads configuration errors across environments
- Red flag: Excessive use of var.* in deeply nested modules, missing validation, no defaults

**Check: Security Group & Network Configuration**
- What to verify: Least-privilege rules, ingress/ingress documentation, CIDR restrictions
- Why it matters: Terraform makes it easy to open everything; explicit review prevents breaches
- Red flag: 0.0.0.0/0 without justification, missing egress rules, undocumented exceptions

**Check: Test Coverage for Modules**
- What to verify: Unit tests, integration tests, validation examples
- Why it matters: Untested modules propagate errors silently across infrastructure
- Red flag: No test directory, missing validation examples, no linting

**DEEPER-DIVE CHECKS**

**Check: State Management & Locking**
- What to verify: Remote state backend, locking mechanism, state encryption
- Why it matters: State corruption destroys infrastructure; no locking causes collisions
- Red flag: Local state in production, missing locking, unencrypted state files

**Check: Resource Lifecycle & Dependencies**
- What to verify: Explicit dependencies, lifecycle hooks, destruction order
- Why it matters: Implicit dependencies fail during destruction; orphans rack up costs
- Red flag: Missing `depends_on`, no lifecycle rules, orphaned resources in console

---

#### Configuration Management (Ansible)

**FIRST-LEVEL CHECKS**

**Check: Role Structure & Reusability**
- What to verify: Single responsibility, variable interfaces, documentation
- Why it matters: Bloated roles become unmaintainable; unclear interfaces cause configuration drift
- Red flag: Roles doing multiple unrelated things, missing defaults, no role README

**Check: Idempotency Guarantees**
- What to verify: Handler triggers, changed_when usage, conditional logic
- Why it matters: Non-idempotent playbooks break on re-run; false changes trigger restarts
- Red flag: Using `command` without `changed_when`, shell scripts without idempotency checks

**Check: Alerting & Monitoring Integration**
- What to verify: Health check endpoints, log aggregation, alerting rules
- Why it matters: Configured systems are blind without observability; failures go unnoticed
- Red flag: No health checks, missing log shipping, no alerting configuration

**DEEPER-DIVE CHECKS**

**Check: Test Infrastructure (Molecule)**
- What to verify: Test scenarios, verification steps, CI integration
- Why it matters: Untested roles break in production; tests document expected behavior
- Red flag: No molecule directory, missing verification playbooks, tests not in CI

**Check: Secret Management**
- What to verify: Vault integration, secret rotation, no plain-text credentials
- Why it matters: Secrets in git or vars files leak; manual rotation fails
- Red flag: Passwords in group_vars, missing Vault references, no rotation mechanism

---

#### Data Infrastructure

**FIRST-LEVEL CHECKS**

**Check: Replication & Backup Verification**
- What to verify: Replication lag monitoring, backup integrity tests, restore procedures
- Why it matters: Silent replication failures and corrupt backups only surface when needed
- Red flag: No lag alerts, untested restores, missing integrity checks

**Check: Data Masking & Scrubbing Logic**
- What to verify: PII detection accuracy, masking completeness, access controls
- Why it matters: Incomplete masking leaks PII; regulatory compliance requires proof
- Red flag: Hardcoded masks, missing fields in scrubbing rules, no audit trail

**Check: Migration Runbook Completeness**
- What to verify: Rollback steps, validation queries, escalation procedures
- Why it matters: Failed migrations without rollback plans cause extended outages
- Red flag: Missing rollback steps, no validation criteria, incomplete timing estimates

**DEEPER-DIVE CHECKS**

**Check: API Design for Data Access**
- What to verify: Pagination, filtering, rate limiting, query optimization
- Why it matters: Poor API design causes database overload and timeouts
- Red flag: Unbounded queries, missing indexes, no rate limiting

**Check: Logical Replication & CDC**
- What to verify: Slot management, conflict resolution, schema change handling
- Why it matters: Replication slots accumulate WAL; conflicts cause data divergence
- Red flag: Inactive slots, no conflict strategy, schema changes breaking replication

---

#### Observability & Monitoring

**FIRST-LEVEL CHECKS** *[extrapolated from tf_enova_datadog, enova_datadog Ansible role]*

**Check: Metrics Coverage**
- What to verify: Service-level indicators defined, infrastructure metrics collected, business metrics tracked
- Why it matters: You can't manage what you don't measure; gaps mean blind spots during incidents
- Red flag: No SLIs defined, missing infrastructure metrics, no correlation between technical and business metrics

**Check: Alerting Hygiene**
- What to verify: Alert fatigue metrics, actionable alerts only, proper routing, runbooks attached
- Why it matters: Alert fatigue causes on-call burnout; unactionable alerts are ignored
- Red flag: >20 alerts/day per service, alerts without runbooks, no PagerDuty/Slack routing

**Check: Real User Monitoring (RUM)**
- What to verify: Frontend performance tracking, user journey correlation, error attribution
- Why it matters: Backend metrics miss user experience; RUM catches what synthetic monitoring can't
- Red flag: No frontend telemetry, RUM data not tied to backend traces, missing Core Web Vitals

**DEEPER-DIVE CHECKS** *[ADD FROM EXPERIENCE: Memory leak investigation patterns, container restart RCA]*

**Check: Distributed Tracing**
- What to verify: Trace context propagation, sampling strategy, span coverage
- Why it matters: Without tracing, debugging across services is guesswork
- Red flag: Broken trace chains, no sampling configuration, missing critical spans

**Check: Log Retention & Queryability**
- What to verify: Retention policies, query performance, cost vs coverage tradeoffs
- Why it matters: 30-day retention is useless for quarterly analysis; slow queries hinder incident response
- Red flag: No retention strategy, queries >10s, log volume growing unchecked

**Check: SLOs & Error Budgets**
- What to verify: Defined SLOs, error budget tracking, burn rate alerts
- Why it matters: Reliability without SLOs is just hoping nothing breaks
- Red flag: No SLOs, SLOs without alerts, error budgets not reviewed

---

#### Security & Identity

**FIRST-LEVEL CHECKS** *[extrapolated from tf_enova_vault_app_role, ldap2pg, vendor-diligence-agent]*

**Check: Secret Management**
- What to verify: Vault/AppRole usage, rotation policies, audit logging, no hardcoded secrets
- Why it matters: Secrets in code/config are breaches waiting to happen; rotation limits blast radius
- Red flag: Hardcoded credentials, no rotation policy, missing Vault audit logs

**Check: Identity Synchronization**
- What to verify: LDAP/AD sync, group mappings, offboarding automation, orphaned accounts
- Why it matters: Stale accounts are attack vectors; manual identity management doesn't scale
- Red flag: Manual account creation, no offboarding workflow, group memberships not audited

**Check: Authentication Flows**
- What to verify: MFA enforcement, SSO integration, session management, API key governance
- Why it matters: Weak auth is the #1 compromise vector; poor UX drives shadow IT
- Red flag: MFA bypasses allowed, long-lived sessions, API keys without rotation

**DEEPER-DIVE CHECKS** *[ADD FROM EXPERIENCE: OAuth/OIDC implementation review, OAuth consent flow assessment]*

**Check: Authorization Model**
- What to verify: RBAC clarity, least privilege enforcement, privilege escalation paths
- Why it matters: Over-permissioned users increase blast radius; unclear roles cause access requests chaos
- Red flag: "Full admin" as default role, no privilege review process, shared service accounts

**Check: Vendor Security Assessment**
- What to verify: Third-party risk scoring, compliance attestation, data residency
- Why it matters: You inherit your vendors' security posture; SaaS sprawl creates blind spots
- Red flag: No vendor security review, SOC2 reports not validated, data residency unclear

---

#### Event Streaming & Data Movement

**FIRST-LEVEL CHECKS** *[extrapolated from tf_enova_kafka_managed_connector, Kafka monitors, Debezium work]*

**Check: Stream Topology Health**
- What to verify: Producer/consumer lag, partition balance, replication factor, unclean leader election
- Why it matters: Streaming platforms are only as healthy as their weakest partition
- Red flag: Persistent consumer lag, hot partitions, under-replicated topics

**Check: Connector Reliability**
- What to verify: JDBC/task configs, error handling, checkpoint management, retry policies
- Why it matters: Connectors are glue; when they fail, data pipelines break silently
- Red flag: No dead letter queue, checkpoint corruption, missing error handling

**Check: Schema Evolution**
- What to verify: Schema registry usage, backward/forward compatibility, breaking change detection
- Why it matters: Schema changes break consumers; unmanaged evolution causes production incidents
- Red flag: No schema registry, manual schema updates, consumers not validated against schemas

**DEEPER-DIVE CHECKS** *[ADD FROM EXPERIENCE: Stream catalog tagging strategy, JDBC connector credential management]*

**Check: Data Consistency Guarantees**
- What to verify: Exactly-once semantics, ordering guarantees, duplicate detection
- Why it matters: Financial/real-time systems need strong consistency; "at-least-once" may not suffice
- Red flag: No idempotency handling, undefined ordering semantics, duplicates in downstream systems

**Check: CDC Pipeline Health**
- What to verify: Debezium slot management, schema change capture, target lag metrics
- Why it matters: CDC lag causes data staleness; slot issues can halt replication entirely
- Red flag: Slot accumulation without cleanup, no lag alerts, schema changes breaking CDC

---

#### CI/CD & Delivery

**FIRST-LEVEL CHECKS** *[extrapolated from ci_cd_pipeline_jobs, CircleCI configs, enova_deploy work]*

**Check: Pipeline Speed**
- What to verify: Build time trends, parallelization, caching effectiveness, flaky test impact
- Why it matters: Slow pipelines kill developer flow; 10+ minute builds indicate serious waste
- Red flag: Build time >15min, no caching, sequential jobs that could parallelize, flaky tests blocking deploys

**Check: Deployment Safety**
- What to verify: Rollback capability, health checks, canary/blue-green support, blast radius containment
- Why it matters: Deployment without rollback is gambling; bad deploys should be revertible in seconds
- Red flag: No rollback procedure, deploys directly to production, missing health check gates

**Check: Artifact Management**
- What to verify: Immutable artifacts, vulnerability scanning, retention policies, provenance tracking
- Why it matters: Reproducible builds require immutable artifacts; scanned images reduce CVE exposure
- Red flag: Mutable artifacts, no scanning, unclear image provenance, no signing

**DEEPER-DIVE CHECKS** *[ADD FROM EXPERIENCE: Jenkins shared library patterns, matrix build optimization]*

**Check: Test Strategy**
- What to verify: Unit vs integration vs E2E balance, coverage trends, test data management
- Why it matters: Test gaps manifest as production bugs; slow tests reduce iteration speed
- Red flag: No integration tests, <50% coverage, shared test data causing flakes

**Check: Environment Parity**
- What to verify: Prod-like staging, data anonymization, configuration drift detection
- Why it matters: "Works on my machine" is often environment parity failure
- Red flag: Staging uses different configs, production data in lower envs, manual environment setup

---

#### Documentation & Knowledge Systems

**FIRST-LEVEL CHECKS**

**Check: Cross-Reference Accuracy**
- What to verify: Internal links, code references, architecture diagrams
- Why it matters: Stale docs waste more time than no docs; bad references cause errors
- Red flag: 404s in internal links, code that doesn't match docs, outdated diagrams

**Check: Coherence Across Documents**
- What to verify: Consistent terminology, aligned patterns, non-contradictory guidance
- Why it matters: Conflicting docs confuse teams; inconsistency signals process gaps
- Red flag: Different patterns for same problem, undefined terms, contradictory standards

**Check: Getting Started Completeness**
- What to verify: Prerequisites, first commands, common pitfalls, validation steps
- Why it matters: New team members get stuck on day one; incomplete onboarding kills momentum
- Red flag: Missing prerequisites, no validation steps, undocumented manual setup

**DEEPER-DIVE CHECKS**

**Check: Architecture Decision Record (ADR) Trail**
- What to verify: Decisions documented, context captured, status current
- Why it matters: Undocumented decisions get re-litigated; missing context causes repeated mistakes
- Red flag: No ADR directory, decisions without context, stale "proposed" ADRs

---

#### Developer Experience (Backstage, Portals)

**FIRST-LEVEL CHECKS**

**Check: Auth/Permissions Integration**
- What to verify: SSO flow, group mapping, permission enforcement
- Why it matters: Portal without proper auth becomes security liability; manual access is friction
- Red flag: Hardcoded users, missing group sync, overly permissive defaults

**Check: API Integration Health**
- What to verify: Error handling, loading states, timeout management
- Why it matters: Developer portals aggregate many services; any failure degrades experience
- Red flag: Missing error states, no loading indicators, unhandled timeouts

---

### 11. Consumer Lending & Financial Systems

**First-Level (Week 1-2)**
- [ ] Loan origination system: uptime SLA, latency p95, deployment frequency
- [ ] Payment processing: PCI-DSS compliance current? Last assessment date?
- [ ] Collections system: integration points, manual vs automated workflows
- [ ] Underwriting engine: model versioning, A/B testing capability, rollback procedure
- [ ] Customer data platform: single source of truth or fragmented across systems?
- [ ] Regulatory reporting: automated or manual? How many person-hours per report?
- [ ] State-by-state lending compliance: how are rate caps, disclosure requirements enforced in code?

**Deeper Dive**
- [ ] Loan origination to servicing handoff: data loss, manual steps, reconciliation failures
- [ ] Payment processor redundancy: what happens if primary processor goes down?
- [ ] Fraud detection: real-time vs batch? False positive rate? Manual review queue depth?
- [ ] Customer communication systems: regulatory disclosure delivery (email, SMS, mail) with audit trail
- [ ] Data lineage from application to reporting: can you trace a loan decision back to source data?
- [ ] Disaster recovery for financial systems: RPO/RTO for loan origination, payment processing
- [ ] Third-party data providers (credit bureaus, income verification): redundancy and contract terms

### 12. Regulatory Compliance & Audit Readiness

**First-Level (Week 1-2)**
- [ ] SOX controls inventory: documented? Last tested? Who owns each control?
- [ ] PCI-DSS scope: which systems are in scope? Last QSA assessment date and findings?
- [ ] State lending license compliance: automated rate/fee cap enforcement per state?
- [ ] GLBA safeguards: information security program documented and tested?
- [ ] Consumer data retention and destruction: policy exists? Automated enforcement?
- [ ] Audit trail coverage: all financial transactions have immutable audit logs?
- [ ] Change management: all production changes to financial systems go through CAB/approval?

**Deeper Dive**
- [ ] SOX IT General Controls (ITGCs): access management, change management, backup/recovery, operations
- [ ] PCI-DSS compensating controls: any in place? Documented rationale?
- [ ] State regulatory exam readiness: can you produce required reports within 48 hours of examiner request?
- [ ] Data residency: consumer financial data stays within required jurisdictions?
- [ ] Vendor compliance chain: do all Tier 1 vendors have current SOC 2 Type II, PCI-DSS attestation?
- [ ] Incident response for data breaches: plan tested? State notification requirements mapped?
- [ ] Model risk management (SR 11-7 if applicable): underwriting model validation, documentation, governance

---

## Usage Instructions

### For Architecture Assessment

1. **Start with domain identification**: What type of system are you assessing? (IaC, AI platform, data pipeline, etc.)

2. **Run first-level checks**: Quick pass through initial assessment items - these surface obvious issues fast

3. **Deep-dive based on findings**: If first-level checks reveal red flags, use deeper-dive checks in those domains

4. **Track blind spots**: Note which domains you couldn't assess thoroughly - these require external expertise

### For Building Assessment Capability

1. **Map your coverage**: Count how many checks you can execute in each domain

2. **Identify weak domains**: Any domain with <3 checks is a blind spot requiring development

3. **Prioritize depth over breadth**: Master 5-6 checks deeply rather than 20 superficially

4. **Build reference library**: Document real examples of red flags encountered

### Output Format

When conducting an assessment, produce:

```markdown
# Architecture Assessment: [System Name]

## Executive Summary
- **Overall Health**: [Green/Yellow/Red]
- **Critical Issues**: [Count] blocking issues found
- **Domains Assessed**: [List]
- **Blind Spots**: [Domains not assessed]

## Domain Findings

### [Domain Name]
**Status**: ✅ Healthy / ⚠️ Concerns / 🚨 Critical

**Passed Checks**:
- [Check name]: [Brief evidence]

**Failed Checks**:
- [Check name]: [What was found] → [Recommended action]

## Blind Spot Acknowledgment
Domains not assessed in this review:
- [Domain]: [Why - lack of expertise, no access, out of scope]

## Recommendations
Prioritized actions based on risk and effort
```

### Domain Summary Matrix

| Domain | Health | Critical Findings | Cost Impact | Regulatory Risk | Priority |
|--------|--------|-------------------|-------------|-----------------|----------|
| [Domain name] | 🟢/🟡/🔴 | [Count] | $[annual] or [effort-hours] | None/Low/Medium/High/Critical | P1/P2/P3 |

> **PE Reporting Note**: Every Yellow or Red finding must include estimated cost impact (annual $ or effort-hours) and regulatory risk level (None/Low/Medium/High/Critical). Findings without business impact quantification will not get executive attention.

## Cross-Skill Integration

### After Assessment Completes
| Finding Type | Next Skill | Action |
|---|---|---|
| Decision needed (build/buy/migrate) | **decision-engine** | Create ADR with assessment findings as context |
| Vendor risk or consolidation opportunity | **vendor-evaluator** | Trigger vendor evaluation with assessment data as input |
| Present findings to leadership | **executive-framer** | Use Executive Summary template or Risk Translation template |
| Operational gaps found | **runbook-generator** | Generate runbooks for undocumented critical procedures |
| Infrastructure standards needed | **terraform-module-scaffold** | Scaffold modules that enforce discovered standards |
| System needs migration or modernization | **migration-playbook** | Create phased migration plan with scope, sequencing, and rollback |

### Assessment Feeds These Outputs
- **90-Day Architecture Report** → executive-framer (Executive Summary template)
- **Critical Risk Findings** → executive-framer (Risk Translation template) + decision-engine (urgent ADR)
- **Vendor Portfolio Analysis** → vendor-evaluator (full evaluation) + executive-framer (Vendor Assessment template)
- **Compliance Gaps** → runbook-generator (audit procedures) + executive-framer (Risk Translation)
- **Migration-Worthy Systems** → migration-playbook (Phase 0 scope document) + executive-framer (Investment Justification)

## Domain Maturity Model

Use this to position your assessment capabilities:

| Level | Description | Indicators |
|-------|-------------|------------|
| **Ad-hoc** | Spot checks based on intuition | No checklist, findings vary by reviewer |
| **Consistent** | Repeatable first-level checks | Standard checklist, consistent coverage |
| **Deep** | Deep-dive capability in key domains | Can assess edge cases, know failure modes |
| **Comprehensive** | Coverage across all critical domains | Multi-domain expertise, tool-supported |
| **Predictive** | Identify issues before they manifest | Pattern libraries, proactive detection |

#### Financial Services Maturity Overlay
For regulated financial services, add these to each level assessment:
- **Level 1 (Ad-hoc)**: No documented compliance controls; audit would find material weaknesses
- **Level 2 (Repeatable)**: Compliance controls exist but are manually executed; audit prep takes weeks
- **Level 3 (Defined)**: Compliance controls documented and partially automated; audit prep takes days
- **Level 4 (Managed)**: Compliance-as-code for most controls; continuous compliance monitoring; audit-ready always
- **Level 5 (Predictive)**: Proactive compliance; regulatory changes detected and implemented before deadlines

## Continuous Improvement

### After Each Assessment

1. **Update patterns**: Did you find a new red flag? Add it to the checklist
2. **Share findings**: Publish anonymized patterns to build team knowledge
3. **Calibrate severity**: Were red flags actually critical? Adjust based on outcomes
4. **Expand coverage**: Pick one blind spot to develop each quarter

### Building Your Pattern Library

Document real examples of:
- **Red flags encountered**: What did you see?
- **Impact**: What happened as a result?
- **Detection method**: How did you find it?
- **Remediation**: How was it fixed?

This library becomes your secret weapon for rapid assessment and credibility building.
