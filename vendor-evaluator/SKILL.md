---
name: vendor-evaluator
description: "Evaluate vendors, tools, and platforms with structured scoring, risk assessment, and financial analysis. Use when evaluating a vendor, assessing a tool or platform, comparing alternatives, conducting due diligence on a SaaS product, planning vendor consolidation, renegotiating contracts, or when someone asks 'should we buy this'. Produces scored evaluation reports with TCO analysis, compliance verification, and executive-ready recommendation memos tied to cost, risk, and consolidation impact."
---

# Vendor Evaluator: Technology & Vendor Assessment Framework

Your documented methodology for evaluating external vendors and platforms based on analysis of vendor diligence, IT risk, and technology assessment sessions.

## When to Use This Skill

- Evaluating SaaS providers for enterprise adoption
- Assessing technology vendors for platform decisions
- Conducting IT risk diligence on third-party services
- Comparing multiple vendors against criteria
- Making build vs. buy vs. integrate decisions
- Creating vendor scorecards for leadership

---

## PE-Backed Financial Services Vendor Context

### PE Vendor Evaluation Priorities
At a PE-backed company, vendor evaluations serve dual purposes: operational fitness AND portfolio optimization.

1. **Vendor consolidation opportunity** - Can this vendor replace 2+ existing vendors? PE sponsors track total vendor count as a cost efficiency metric.
2. **Contract leverage** - Is the vendor in a competitive market? Can we negotiate better terms? Multi-year commits acceptable only with significant discount (25%+).
3. **Exit cost** - What does it cost to leave this vendor in 3 years? PE exits require clean technology stacks.
4. **Portfolio synergy** - Do other portfolio companies use this vendor? Can we negotiate portfolio-wide pricing?

### Financial Services Compliance Requirements
Add these to EVERY Tier 1 vendor evaluation:

```markdown
#### Regulatory Compliance Verification
| Requirement | Status | Evidence | Expiration |
|-------------|--------|----------|------------|
| SOC 2 Type II report | ✅/❌ | [Link/date] | [Date] |
| PCI-DSS attestation (if handling payment data) | ✅/❌/N/A | [Link/date] | [Date] |
| SOX-relevant controls documentation | ✅/❌/N/A | [Description] | — |
| GLBA safeguards compliance | ✅/❌/N/A | [Link/date] | — |
| State data residency requirements met | ✅/❌ | [Description] | — |
| Data processing agreement (DPA) signed | ✅/❌ | [Date signed] | — |
| Right to audit clause in contract | ✅/❌ | [Contract section] | — |
| Breach notification SLA (≤24 hours) | ✅/❌ | [Contract section] | — |
| Consumer data deletion capability | ✅/❌ | [Process documented] | — |
| Subprocessor notification requirement | ✅/❌ | [Contract section] | — |
```

### Financial Services Red Flags (Automatic Disqualifiers)
In addition to the standard red flags, these are automatic disqualifiers for financial services:
- [ ] **No SOC 2 Type II** — Non-negotiable for any vendor handling our data
- [ ] **No right to audit** — We must be able to audit or have third-party audit rights
- [ ] **Data residency outside US** — Consumer financial data must stay within US jurisdiction unless explicitly approved by Legal
- [ ] **No breach notification SLA** — Must commit to notification within 24 hours
- [ ] **Cannot provide data deletion** — CCPA and state privacy laws require this capability
- [ ] **Shared tenancy without logical isolation** — PCI-DSS requires network segmentation

---

## Evaluation Framework Overview

### The 4-Stage Assessment Workflow

Based on your IT diligence patterns, every vendor evaluation follows:

1. **Intake** → Collect vendor/service basics
2. **Classification** → Determine inherent risk tier
3. **Review** → Deep-dive on tier-appropriate criteria
4. **Finalized** → Score, recommend, and document

---

## Stage 1: Intake & Context Gathering

### Standard Intake Questions

```markdown
# Vendor Intake Template

## Basic Information
- **Vendor/Service Name**: 
- **Primary Service Category**: [Infrastructure / SaaS / Security / Data / etc.]
- **Provider Description**: [What they do in 1-2 sentences]
- **Deployment Model**: [Cloud-native / On-prem / Hybrid / Multi-tenant]
- **Geographic Scope**: [US-only / EU / Global / Specific regions]

## Business Context
- **Proposed Use Case**: [What problem we're solving]
- **Integration Points**: [Systems this touches]
- **Data Involved**: [What data types flow through this]
- **User Population**: [Internal only / External customers / Both]
- **Business Criticality**: [Critical / High / Medium / Low]

## Initial Red Flags (Pass/Fail Gates)
- [ ] Vendor is in bankruptcy or acquisition talks
- [ ] No SOC2 Type II or equivalent attestation
- [ ] Data residency requirements cannot be met
- [ ] Requires infrastructure we don't support (e.g., Windows-only, specific cloud)
- [ ] Prohibitive cost (>2x budget without clear ROI)
- [ ] Known security incidents in past 12 months

**If any red flag is checked → Escalate to security/compliance before proceeding**
```

---

## Stage 2: Risk Classification (Tier Assignment)

### Risk Tier Matrix

Your evaluation uses a 2-tier system based on data sensitivity × business impact:

| Data Sensitivity | Critical Business Impact | High Business Impact | Medium Business Impact | Low Business Impact |
|------------------|--------------------------|---------------------|---------------------|---------------------|
| **High** (PHI, PII, financial, proprietary) | **TIER 1** | **TIER 1** | **TIER 1** | **TIER 2** |
| **Medium-High** (employee data, customer lists) | **TIER 1** | **TIER 1** | **TIER 2** | **TIER 2** |
| **Medium** (analytics, non-sensitive operational) | **TIER 1** | **TIER 2** | **TIER 2** | **TIER 2** |
| **Low** (public data, anonymized metrics) | **TIER 2** | **TIER 2** | **TIER 2** | **TIER 2** |

### Tier Definitions

**TIER 1 (High Risk)**
- Full IT Risk Diligence Questionnaire (52+ questions)
- Security review with architecture diagrams
- Compliance attestation validation
- Legal review of terms
- Executive approval required

**TIER 2 (Standard Risk)**
- Abbreviated questionnaire (20-30 questions)
- Standard security review
- SOC2 attestation check
- Department head approval

---

## Stage 3: Deep-Dive Review by Tier

### Tier 1: Comprehensive Diligence Checklist

#### 1. Security & Compliance (Weight: 25%)

**Access Control**
- [ ] MFA enforcement for all admin accounts
- [ ] Role-based access control (RBAC) granularity
- [ ] Privileged access monitoring and logging
- [ ] Automated user provisioning/deprovisioning
- [ ] API key rotation policies

**Data Protection**
- [ ] Encryption at rest (AES-256 or equivalent)
- [ ] Encryption in transit (TLS 1.2+)
- [ ] Key management (HSM, key rotation)
- [ ] Data classification capabilities
- [ ] DLP (Data Loss Prevention) features

**Compliance Attestations**
- [ ] SOC2 Type II (last 12 months)
- [ ] ISO 27001 certification
- [ ] GDPR compliance documentation
- [ ] Industry-specific (HIPAA, PCI-DSS if applicable)
- [ ] Penetration test results (last 12 months)

**Incident Response**
- [ ] Documented incident response plan
- [ ] Breach notification SLA (<24 hours)
- [ ] Forensic capabilities
- [ ] Customer communication protocols

#### 2. Architecture & Integration (Weight: 20%)

**Technical Fit**
- [ ] API availability (REST/GraphQL/gRPC)
- [ ] Authentication methods (OAuth2, SAML, OIDC)
- [ ] Webhook/event support
- [ ] Rate limiting and quotas
- [ ] SDK availability for our stack

**Integration Complexity**
- [ ] Existing integrations with our tools
- [ ] Middleware requirements
- [ ] Custom development needed
- [ ] Migration effort estimation

**Scalability**
- [ ] Proven scale (users/transactions/data volume)
- [ ] Performance SLAs
- [ ] Auto-scaling capabilities
- [ ] Geographic redundancy

#### 3. Operational Resilience (Weight: 15%)

**Availability & Reliability**
- [ ] Uptime SLA (99.9% minimum, 99.99% preferred)
- [ ] RTO/RPO commitments
- [ ] Multi-region deployment
- [ ] Maintenance window policies

**Monitoring & Observability**
- [ ] Status page with real-time metrics
- [ ] Alerting integration (PagerDuty, etc.)
- [ ] Audit logging (90+ days retention)
- [ ] Log export capabilities

**Support & Escalation**
- [ ] Support tiers and SLAs
- [ ] Escalation paths
- [ ] Dedicated account manager (for Tier 1)
- [ ] Documentation quality

#### 4. Vendor Viability & Exit Risk (Weight: 15%)

**Financial Health**
- [ ] Funding stage/revenue (public or disclosed)
- [ ] Customer count and growth
- [ ] Burn rate (if startup)
- [ ] Acquisition risk assessment

**Product Roadmap**
- [ ] Public roadmap available
- [ ] Feature request process
- [ ] Deprecation policies
- [ ] Backward compatibility commitments

**Exit Strategy**
- [ ] Data export capabilities
- [ ] API contract stability
- [ ] Migration assistance offered
- [ ] No vendor lock-in (standards-based)

#### 5. Cost & Consolidation Impact (Weight: 25%)

**Pricing Model**
- [ ] Transparent pricing
- [ ] Predictable costs (no surprise overages)
- [ ] Volume discounts
- [ ] Multi-year commitments available

**Contract Terms**
- [ ] Liability caps (adequate for risk)
- [ ] Indemnification
- [ ] Termination rights (30-day minimum)
- [ ] Data deletion post-termination

---

### Tier 2: Standard Diligence Checklist

For Tier 2 vendors, focus on high-impact items only:

#### Critical Must-Haves (Disqualifiers if Missing)
- [ ] SOC2 Type II or ISO 27001
- [ ] Encryption at rest and in transit
- [ ] MFA support
- [ ] 99.9% uptime SLA
- [ ] Breach notification <48 hours
- [ ] Data residency compliance

#### Important Evaluation Factors
- [ ] Integration effort (<2 weeks preferred)
- [ ] Support quality (responsive, knowledgeable)
- [ ] Pricing predictability
- [ ] Documentation adequacy
- [ ] Vendor financial stability (not acutely distressed)

---

## Stage 4: Scoring & Recommendation

### Weighted Scoring Rubric

```markdown
# Vendor Scorecard

## Overall Score: [X] / 100

### Breakdown by Category

| Category | Weight | Score (0-10) | Weighted Score |
|----------|--------|--------------|----------------|
| Security & Compliance | 25% | [ ] | [ ] |
| Architecture & Integration | 20% | [ ] | [ ] |
| Operational Resilience | 15% | [ ] | [ ] |
| Vendor Viability & Exit Risk | 15% | [ ] | [ ] |
| Cost & Consolidation Impact | 25% | [ ] | [ ] |
| **TOTAL** | **100%** | - | **[ ]** |

### Scoring Guide
- **10**: Exceptional, best-in-class, exceeds requirements
- **8-9**: Strong, meets all requirements comfortably
- **6-7**: Adequate, meets minimum requirements
- **4-5**: Weak, gaps in critical areas
- **0-3**: Unacceptable, missing fundamental capabilities
```

> **Weight Rationale**: In a PE-backed environment, Cost & Consolidation Impact carries 25% (not the typical 10%) because vendor spend optimization is a primary PE value creation lever. Security & Compliance is non-negotiable but scored at 25% because failures here are captured as automatic disqualifiers, not scored on a sliding scale.

### Recommendation Matrix

| Overall Score | Recommendation | Action |
|---------------|----------------|--------|
| **85-100** | **APPROVE** | Proceed with standard contract terms |
| **70-84** | **APPROVE WITH CONDITIONS** | Address specific gaps before onboarding |
| **55-69** | **CONDITIONAL** | Significant concerns; requires mitigation plan |
| **40-54** | **REJECT** | Does not meet minimum requirements |
| **0-39** | **REJECT** | Critical deficiencies; high risk |

### Vendor Consolidation Assessment
For every vendor evaluation, also assess consolidation impact:

```markdown
#### Consolidation Analysis
| Factor | Assessment |
|--------|-----------|
| **Vendors this could replace** | [List specific vendors and their annual cost] |
| **Net cost change** | [New vendor cost] - [Eliminated vendor costs] = $X/year |
| **Migration effort** | [Low/Medium/High] — estimated [N] engineer-weeks |
| **Consolidation timeline** | [N months] to full cutover |
| **Contract exit costs** | [$ for early termination of replaced vendors] |
| **Risk during transition** | [Description of dual-running period risks] |
| **Portfolio leverage** | [Can other portfolio companies use this pricing?] |

**Consolidation Score**: 
- **High value**: Replaces 2+ vendors with net savings > $100K/year
- **Medium value**: Replaces 1 vendor or net savings $25K-$100K/year
- **Low value**: No consolidation opportunity
- **Negative**: Adds a new vendor without replacing any
```
> **PE Reporting Note**: Any evaluation that results in adding a net-new vendor (increasing total vendor count) requires explicit justification in the recommendation memo explaining why consolidation was not possible.

---

## Total Cost of Ownership (TCO) Analysis

### 5-Year TCO Framework

```markdown
# TCO Analysis: [Vendor Name]

## Direct Costs

### Year 1
- License/Subscription: $[ ]
- Implementation: $[ ]
- Integration development: $[ ]
- Training: $[ ]
- **Year 1 Total**: $[ ]

### Years 2-5 (Annual)
- License/Subscription: $[ ]/year
- Support/Maintenance: $[ ]/year
- Infrastructure (if applicable): $[ ]/year
- **Annual Run Rate**: $[ ]

**5-Year Total Direct**: $[ ]

## Indirect Costs

| Cost Category | Year 1 | Years 2-5 (annual) |
|---------------|--------|---------------------|
| Internal admin time (FTE %) | [ ]% | [ ]% |
| Opportunity cost (projects delayed) | $[ ] | $[ ] |
| Risk exposure (incident probability × impact) | $[ ] | $[ ] |
| Training (ongoing) | $[ ] | $[ ] |

## Cost Avoidance (What We No Longer Need)

| Current State Cost | Annual Savings |
|-------------------|----------------|
| [Current tool/process] | $[ ] |
| [Manual effort automated] | $[ ] |
| **Total Annual Avoidance** | **$[ ]** |

## Payback Period
**Break-even**: [X] months
**3-Year ROI**: [X]%
**5-Year ROI**: [X]%

## Risk-Adjusted TCO
**Base TCO**: $[ ]
**Risk Premium** (probability of switching costs): +$[ ]
**Risk-Adjusted 5-Year TCO**: $[ ]
```

---

## Red Flags: Automatic Disqualifiers

### Security Red Flags (Instant Reject)
- No encryption at rest for sensitive data
- Single-factor authentication only
- No SOC2 or equivalent attestation
- History of undisclosed breaches
- No incident response plan
- Refuses security questionnaire

### Operational Red Flags (Proceed with Extreme Caution)
- <99.5% uptime SLA
- No disaster recovery plan
- Data residency cannot be guaranteed
- No API access
- Vendor in financial distress
- Product in maintenance mode

### Commercial Red Flags (Negotiation Blockers)
- Opaque pricing with surprise overages
- Excessive liability caps (<$1M for Tier 1)
- No data deletion on termination
- Prohibitive exit costs
- Mandatory 3+ year contracts

### Integration Red Flags (High Complexity Warning)
- Requires custom middleware
- No API, only UI automation
- Proprietary data formats
- No webhook/event support
- Black-box system (no observability)

---

## Recommendation Memo Template

```markdown
# Vendor Assessment Recommendation

**Vendor**: [Name]
**Service**: [What they provide]
**Assessment Date**: [Date]
**Assessor**: [Name]
**Risk Tier**: [Tier 1 / Tier 2]

## Executive Summary

**Recommendation**: [APPROVE / APPROVE WITH CONDITIONS / CONDITIONAL / REJECT]

**Overall Score**: [X] / 100

**One-Sentence Rationale**: [Why this recommendation]

## Business Case

**Problem We Solve**: [Current gap and business impact]

**Solution**: [What vendor provides]

**Alternatives Considered**:
| Alternative | Why Not Selected |
|-------------|------------------|
| [Option B] | [Specific gap] |
| [Option C] | [Specific gap] |
| Build in-house | [Time/cost/risk] |

## Assessment Summary

### Strengths
- [Strength 1]: [Evidence]
- [Strength 2]: [Evidence]
- [Strength 3]: [Evidence]

### Concerns
- [Concern 1]: [Evidence + mitigation if applicable]
- [Concern 2]: [Evidence + mitigation if applicable]

### Score Breakdown
| Category | Score | Notes |
|----------|-------|-------|
| Security | [ ] | [Key finding] |
| Integration | [ ] | [Key finding] |
| Operations | [ ] | [Key finding] |
| Viability | [ ] | [Key finding] |
| Cost | [ ] | [Key finding] |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|---------|------------|
| [Risk 1] | [High/Med/Low] | [High/Med/Low] | [Strategy] |
| [Risk 2] | [High/Med/Low] | [High/Med/Low] | [Strategy] |

## Total Cost of Ownership

- Year 1 Investment: $[ ]
- Annual Run Rate (Years 2-5): $[ ]
- 5-Year TCO: $[ ]
- Payback Period: [X] months

## Conditions (If Applicable)

If **APPROVE WITH CONDITIONS** or **CONDITIONAL**:

| Condition | Owner | Timeline | Validation Criteria |
|-----------|-------|----------|---------------------|
| [Condition 1] | [Name] | [Date] | [How we verify] |
| [Condition 2] | [Name] | [Date] | [How we verify] |

## Required Approvals

- [ ] IT Risk: _________________ Date: _______
- [ ] Security: _________________ Date: _______
- [ ] Legal: _________________ Date: _______
- [ ] Procurement: _________________ Date: _______
- [ ] Executive Sponsor: _________________ Date: _______

## Appendices

- A: Full Diligence Questionnaire Responses
- B: Architecture Review Notes
- C: TCO Detailed Calculations
- D: Vendor Documentation (SOC2, contracts, etc.)
```

---

## Cross-Skill Integration

### Inputs (What Triggers Vendor Evaluation)
| Source Skill | Trigger | Evaluation Type |
|---|---|---|
| **architecture-assessor** | Vendor concentration risk identified | Full Tier 1 evaluation of alternatives |
| **architecture-assessor** | Technology gap requiring vendor solution | Tier 1 or Tier 2 depending on risk |
| **decision-engine** | Build vs buy ADR leans toward buy | Full Tier 1 evaluation of vendor options |
| **decision-engine** | Vendor consolidation decision needed | Comparative evaluation with consolidation scoring |
| Direct request | "Evaluate this vendor" | Standard evaluation per risk tier |

### Outputs (Where Evaluations Go)
| Output | Destination Skill | Action |
|---|---|---|
| Recommendation memo (Approve) | **executive-framer** | Vendor Assessment template for leadership presentation |
| Recommendation memo (Conditional) | **decision-engine** | ADR for conditions/mitigations before proceeding |
| Recommendation memo (Reject) | **decision-engine** | ADR documenting rejection + alternative evaluation |
| Consolidation analysis | **executive-framer** | Cost Rationalization Narrative template |
| Vendor compliance gaps | **runbook-generator** | Procedures for compensating controls or vendor oversight |

### Evaluation → Executive Presentation Flow
1. Complete vendor evaluation (this skill) — produces scored recommendation memo
2. If consolidation opportunity exists — add Consolidation Analysis section
3. Present to leadership — use **executive-framer** Vendor Assessment template (quick) or Investment Justification template (large spend)
4. If approved — use **decision-engine** to create ADR documenting the vendor selection decision
5. If vendor requires infrastructure — use **terraform-module-scaffold** to scaffold integration modules
6. If vendor replaces existing system — use **migration-playbook** to plan the transition from old vendor to new

---

## Evaluation Anti-Patterns to Avoid

### Patterns You've Learned From:

1. **Skipping tier classification**
   - *Mistake*: Treating all vendors the same
   - *Correction*: Always classify first; determines depth of review

2. **Over-weighting features vs. security**
   - *Mistake*: Scoring vendor highly for bells and whistles with weak security
   - *Correction*: Security is 30% weight minimum; can't compensate with features

3. **Ignoring hidden costs**
   - *Mistake*: Looking only at license fees
   - *Correction*: Always calculate 5-year TCO with indirect costs

4. **No exit strategy assessment**
   - *Mistake*: Evaluating onboarding without considering offboarding
   - *Correction*: Data export and contract termination are evaluation criteria

5. **Insufficient red flag enforcement**
   - *Mistake*: Proceeding despite disqualifiers "with workarounds"
   - *Correction*: Red flags are pass/fail gates, not discussion points

---

## Quick Reference: Evaluation Checklist

### Pre-Assessment (Intake)
- [ ] Basic vendor information collected
- [ ] Use case and integration points documented
- [ ] Initial red flags checked
- [ ] Risk tier assigned (Tier 1 or 2)

### Assessment (Review)
- [ ] Appropriate checklist completed (52+ for Tier 1, 20 for Tier 2)
- [ ] Vendor questionnaire responses received
- [ ] Architecture review conducted (Tier 1)
- [ ] References contacted (Tier 1)
- [ ] TCO calculated

### Decision (Finalized)
- [ ] Scorecard completed with weighted scores
- [ ] Recommendation memo written
- [ ] Risk assessment documented
- [ ] Approval signatures obtained
- [ ] Decision logged in vendor registry

---

## For Your Team

Share this framework with:

> "Use this vendor evaluation framework for any third-party service or SaaS adoption. 
> It ensures we:
> - Classify risk appropriately (Tier 1 vs Tier 2)
> - Evaluate consistently across security, integration, operations, viability, cost
> - Calculate true 5-year TCO, not just license fees
> - Document decisions with clear rationale and risk assessment
> 
> **Golden rule**: If a vendor can't pass the red flags, don't proceed—no exceptions."

Update weights and criteria as your risk posture evolves.
