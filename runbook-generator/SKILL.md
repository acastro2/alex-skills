---
name: runbook-generator
description: "Generate operational runbooks, playbooks, and procedures with validation checkpoints, rollback plans, and compliance documentation. Use when writing a runbook, documenting a procedure, creating an operations playbook, building incident response steps, establishing change management procedures, or codifying any operational process. Produces audit-ready runbooks with pre-flight checks, step-by-step procedures, rollback plans, and compliance evidence collection."
---

# Runbook Generator

Your documented patterns for operational documentation based on 50+ runbook sessions across Ansible, infrastructure, and database operations.

---

## When to Use

- Creating deployment or migration procedures
- Documenting incident response steps
- Writing operational procedures for infrastructure changes
- Building Ansible playbooks with verification
- Creating backup/restore procedures

---

## PE-Backed Financial Services Operational Context

### Regulatory Requirements for Operational Procedures
In a regulated consumer lending environment, runbooks are not just operational tools — they are **audit evidence**. Every runbook must support:

1. **Change management compliance** - SOX requires documented, approved change procedures for systems that affect financial reporting
2. **Audit trail** - Every execution must produce evidence: who ran it, when, what changed, who approved it
3. **Separation of duties** - The person who writes the change is not the person who approves or executes it in production
4. **Incident response obligations** - State data breach notification laws require documented response procedures with specific timelines

### Mandatory Compliance Sections
Every runbook for a system in regulatory scope MUST include:

```markdown
## Compliance & Change Management

### Regulatory Scope
- [ ] System is in scope for: [SOX / PCI-DSS / GLBA / State Lending / None]
- [ ] Data classification of affected systems: [Public / Internal / Confidential / Restricted]
- [ ] This procedure modifies financial reporting systems: [Yes / No]

### Change Approval Requirements
| Environment | Approval Required | Approver Role | Lead Time |
|-------------|------------------|---------------|-----------|
| Development | None | — | — |
| Staging | Peer review | Senior Engineer | 1 business day |
| Production (non-financial) | CAB approval | Change Manager | 3 business days |
| Production (financial/PCI) | CAB + Compliance approval | Change Manager + Compliance Officer | 5 business days |
| Emergency | Emergency CAB | VP Engineering + Compliance | Post-execution within 24 hours |

### Audit Evidence Collection
At each checkpoint in this runbook, capture:
- [ ] Timestamp (UTC)
- [ ] Executor identity (name + role)
- [ ] Approver identity (name + role) 
- [ ] Before-state snapshot or hash
- [ ] After-state snapshot or hash
- [ ] All command outputs preserved to immutable log

### Post-Execution Compliance
- [ ] Change ticket updated with execution evidence
- [ ] Audit log entries verified as immutable
- [ ] If rollback was triggered: incident record created with root cause
```

---

## Your Runbook Structure

### Universal Sections (Every Runbook)

```markdown
# Runbook: [Operation Name]

## Metadata
- **Author**: [Name]
- **Last Updated**: [Date]
- **Review Cycle**: [Quarterly/After major incident]
- **Related Runbooks**: [Links]

## Purpose
[One-paragraph summary of what this runbook achieves and when to use it]

## Prerequisites

### Knowledge Requirements
- [Required knowledge: e.g., "Ansible playbook execution", "AWS CLI basics"]
- [Access level: e.g., "Database admin privileges"]

### Pre-Flight Checklist
- [ ] [Check 1 with specific command or verification]
- [ ] [Check 2 with specific command or verification]
- [ ] [Check 3 with specific command or verification]

## Variables & Parameters

| Variable | Description | Source | Example |
|----------|-------------|--------|---------|
| `ENVIRONMENT` | Target environment | Command line | `prod`, `staging` |
| `SERVICE_NAME` | Service identifier | Environment var | `payment-api` |

## Procedure

### Step 1: [Action Name]
**Objective**: [What this step accomplishes]

**Command/Action**:
```bash
[Specific command with variables]
```

**Validation**:
- [ ] Expected outcome: [What you should see]
- [ ] Verification command: [How to confirm it worked]

**Rollback Trigger**: [When to stop and rollback]
- [Specific condition that indicates failure]

### Step 2: [Next Action]
...

## Rollback Procedure

### Scenario A: [Failure Point]
**When to use**: [Specific condition]

**Steps**:
1. [Rollback step 1]
2. [Rollback step 2]

**Verification**: [How to confirm rollback succeeded]

### Scenario B: [Alternative Failure Point]
...

## Post-Procedure Validation

- [ ] [Comprehensive check 1]
- [ ] [Comprehensive check 2]
- [ ] [Service health verification]

## Error Handling

### Common Error: [Error Name]
**Symptoms**: [What you'll see]
**Root Cause**: [Why it happens]
**Resolution**: [Step-by-step fix]
**Prevention**: [How to avoid next time]

### Common Error: [Another Error]
...

## Notes & Troubleshooting

- [Operational note 1]
- [Known limitation or workaround]
- [Historical context or previous incident reference]

## Changelog

### [Date] - [Author]
- [Change description]
- [Reason for change]
```

---

## Your Pre-Flight Check Patterns

### Ansible/Configuration Management

```yaml
# Always verify before executing
pre_flight_checks:
  - name: "Verify Ansible version"
    command: ansible --version | head -1
    expected: "ansible 2.15+"
    
  - name: "Check inventory accessibility"
    command: ansible all -i {{ inventory }} --list-hosts
    expected: "hosts (X)"
    
  - name: "Validate playbook syntax"
    command: ansible-playbook --syntax-check {{ playbook }}
    expected: "syntax ok"
    
  - name: "Verify target connectivity"
    command: ansible all -i {{ inventory }} -m ping
    expected: "SUCCESS"
    
  - name: "Check disk space on targets"
    command: ansible all -i {{ inventory }} -a "df -h / | tail -1 | awk '{print \$5}' | sed 's/%//'"
    max_threshold: 80
    
  - name: "Validate variables file exists"
    command: test -f {{ vars_file }}
    required: true
```

### Terraform/Infrastructure

```bash
# Pre-flight validation sequence
1. tofu validate  # or terraform validate
2. tofu plan -out=tfplan  # Review plan output
3. tofu show tfplan  # Verify changes match intent
4. Check state lock: tofu force-unlock -dry-run  # Verify no stale locks
5. Verify backend connectivity
```

### Database Operations

```bash
# Pre-flight for database migrations
1. Check replication lag: SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))/60 AS lag_minutes;
2. Verify backup status: SELECT * FROM pg_stat_user_tables ORDER BY n_tup_upd DESC LIMIT 5;
3. Check active connections: SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
4. Validate disk space: SHOW data_directory; then df -h
5. Test rollback capability: Verify rollback scripts exist and are tested
```

### VM/Clone Operations

```bash
# Pre-flight for VM cloning
1. Verify source VM exists and is accessible
2. Check target datastore capacity: esxcli storage filesystem list
3. Validate network configuration: grep -E "^vlan_|^ip_" /etc/network/config
4. Check DNS resolution: nslookup {{ hostname }}.{{ domain }}
5. Verify credential store access: vault read secret/credentials
```

---

## Step Granularity Standards

### Your Pattern: Progressive Detail

**High-level steps** → **Detailed substeps** → **Verification** → **Error handling**

**Example**:

```markdown
### Step 1: Prepare Environment
**Objective**: Ensure all prerequisites are met before starting migration

**Substeps**:
1.1. Source environment variables:
     ```bash
     source /etc/environment.d/{{ service_name }}.env
     ```
     *Operator note: Verify variables are set: `echo $DB_HOST`*

1.2. Validate database connectivity:
     ```bash
     psql -h $DB_HOST -U $DB_USER -c "SELECT 1;"
     ```
     *Expected: "?column?  1"*

1.3. Check current replication status:
     ```bash
     psql -c "SELECT * FROM pg_stat_replication;"
     ```
     *Acceptable: streaming state, lag < 1 minute*

**Validation Checkpoints**:
- [ ] Environment variables loaded
- [ ] Database connection successful
- [ ] Replication lag acceptable (< 60 seconds)

**Rollback Trigger**: If any check fails, do not proceed. Fix the issue first.
```

### Knowledge Assumptions

**What you assume operators know**:
- Basic Linux commands (ssh, grep, awk, jq)
- How to read error logs
- Their environment's variable names
- Standard tool locations

**What you spell out explicitly**:
- Exact command sequences
- Expected output (with examples)
- Specific file paths
- Error conditions and what they look like
- Who to escalate to and when

---

## Rollback Procedure Patterns

### Pattern 1: Checkpoints with Snapshots

```markdown
## Rollback: Pre-Migration State

**When to rollback**: Any step fails before Step 5 (data migration)

**Prerequisites for rollback**:
- Snapshot created at Step 2
- Backup verified in Step 3

**Rollback Steps**:
1. Stop all active operations:
   ```bash
   systemctl stop {{ service_name }}
   ```

2. Restore from snapshot:
   ```bash
   # If VM clone failed
   virsh destroy {{ new_hostname }}
   virsh undefine {{ new_hostname }}
   # Original remains untouched
   ```

3. Verify original service health:
   ```bash
   systemctl status {{ service_name }}
   curl -s http://localhost:8080/health | jq '.status'
   ```

4. Resume traffic to original:
   ```bash
   # Update load balancer (if already switched)
   ansible-playbook update-lb.yml -e target=original
   ```

**Verification**:
- [ ] Original service responding to health checks
- [ ] No data loss (compare checksums)
- [ ] Monitoring alerts cleared

**Post-Rollback Actions**:
- Document failure reason
- Update runbook with new error case
- Schedule retry with fixes
```

### Pattern 2: Error-Resilient Secondary Services

Based on your VM clone playbook pattern:

```markdown
## Rollback: Secondary Service Failures

**Philosophy**: Secondary services (monitoring, logging) must not block primary operation.

**Decision Matrix**:
| Service | Failure Action | Continue? | Post-Action |
|---------|----------------|-----------|-------------|
| Primary DB | Stop immediately | No | Full rollback |
| Splunk agent | Log warning | Yes | Fix post-procedure |
| Datadog | Log warning | Yes | Fix post-procedure |
| Backup job | Log warning | Yes | Run ad-hoc backup |

**Implementation**:
```bash
# Example: Continue despite secondary failure
if ! systemctl restart splunk-forwarder; then
  echo "WARNING: Splunk agent failed to start. Continuing..."
  echo "Action required: Manually restart splunk-forwarder after procedure"
  echo "Timestamp: $(date)"
fi
```
```

### Incident Response Runbook Template
For systems processing consumer financial data, regulatory breach notification timelines apply.

```markdown
# Incident Response: [Incident Type]

## Severity Classification
| Severity | Definition | Response Time | Notification Required |
|----------|-----------|---------------|-----------------------|
| SEV-1 | Data breach, financial system down, regulatory violation | Immediate | CEO, Compliance, Legal within 1 hour |
| SEV-2 | Service degraded, data integrity concern | 30 minutes | VP Engineering, Compliance within 4 hours |
| SEV-3 | Non-critical system issue, no data impact | 2 hours | Engineering management next business day |
| SEV-4 | Minor issue, no customer impact | Next business day | Team lead |

## Immediate Actions (First 15 Minutes)
1. [ ] **Contain**: [Specific containment steps for this incident type]
2. [ ] **Assess scope**: Number of affected customers/records/transactions
3. [ ] **Preserve evidence**: Snapshot logs, do NOT restart services before capturing state
4. [ ] **Notify**: Per severity table above

## State Notification Requirements (Data Breach)
If consumer PII or financial data is exposed:
- [ ] Determine affected states and their notification deadlines (most require 30-60 days)
- [ ] Legal notified within 1 hour to begin state-by-state analysis
- [ ] Do NOT communicate externally until Legal approves messaging
- [ ] Preserve all evidence for potential regulatory investigation

## Investigation Phase
1. [ ] Timeline reconstruction: What happened and when?
2. [ ] Root cause identification
3. [ ] Scope determination: Which customers, which data, which period?
4. [ ] Remediation plan with timeline

## Recovery Phase
1. [ ] Implement fix per standard change procedures (emergency CAB if needed)
2. [ ] Verify fix with validation checks from this runbook
3. [ ] Monitor for recurrence (enhanced monitoring for 72 hours minimum)

## Post-Incident
1. [ ] Post-incident review within 48 hours
2. [ ] Root cause analysis document
3. [ ] Preventive measures identified and ticketed
4. [ ] Compliance team briefed on findings
5. [ ] Update this runbook with lessons learned
```

---

## Validation Step Patterns

### Validation Types You Use

1. **Syntax Validation**: Before execution
   - `ansible-playbook --syntax-check`
   - `tofu validate`
   - SQL parse without execution

2. **Connectivity Validation**: Before touching data
   - SSH connectivity check
   - Database connection test
   - API health check

3. **State Validation**: After each major step
   - Service status verification
   - Data consistency checks
   - Log validation (errors/warnings)

4. **Functional Validation**: End-to-end
   - Smoke tests
   - Integration tests
   - User acceptance validation

### Validation Step Template

```markdown
**Validation [N]: [What to validate]**

**Method**: [Command or procedure]
```bash
[Specific command]
```

**Expected Result**: [Exact output or condition]
```
[Example output]
```

**Troubleshooting if validation fails**:
1. [First diagnostic step]
2. [Second diagnostic step]
3. [Escalation path]

**Acceptable Thresholds**:
- [ ] Metric 1: [Value] (acceptable range: [min]-[max])
- [ ] Metric 2: [Value] (acceptable range: [min]-[max])
```

---

## Error Handling Patterns

### Common Error Format

```markdown
### Error: [Error Name/Code]

**Symptoms**:
- [What you'll see in logs]
- [What the user/system reports]

**Root Cause**:
[Why this happens - technical explanation]

**Immediate Fix**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Verification**:
[How to confirm it's fixed]

**Prevention**:
- [How to avoid in future]
- [If applicable: code/infrastructure change needed]

**Related Runbooks**:
- [Link to recovery procedure]
- [Link to incident post-mortem]
```

### Your Error Categories

**Category 1: Environment/Precondition Failures**
- Missing environment variables
- Wrong working directory
- Insufficient permissions

**Category 2: Resource/Dependency Failures**
- Database unavailable
- Network timeout
- Disk space full

**Category 3: Logic/Configuration Failures**
- Invalid parameter combination
- Syntax errors
- State conflicts

**Category 4: Post-Condition Failures**
- Validation check failed
- Service not healthy
- Data inconsistency

---

## Variables & Parameters Handling

### Your Pattern: Environment + Command Line

```yaml
# variables.yml template
# This file contains all environment-specific values
# Copy to variables.local.yml and customize (DO NOT COMMIT)

# Required variables
environment: "{{ lookup('env', 'ENVIRONMENT') | default('staging', true) }}"
service_name: "{{ lookup('env', 'SERVICE_NAME') | default('my-service', true) }}"

# Derived variables (computed from required)
db_host: "{{ service_name }}-db.{{ environment }}.internal"
backup_bucket: "s3://backups-{{ environment }}/{{ service_name }}"

# Feature flags
features:
  enable_monitoring: true
  enable_backups: "{{ environment == 'prod' }}"
```

### Usage Pattern

```bash
# Option 1: Environment variables
export ENVIRONMENT=prod
export SERVICE_NAME=payment-api
ansible-playbook -i inventory.yml deploy.yml

# Option 2: Extra vars (override)
ansible-playbook -i inventory.yml deploy.yml \
  -e "environment=prod" \
  -e "service_name=payment-api"

# Option 3: Vars file (recommended for complex deployments)
ansible-playbook -i inventory.yml deploy.yml \
  -e @production_vars.yml
```

### Validation Pattern

```yaml
# At playbook start
- name: "Validate required variables"
  fail:
    msg: "Missing required variable: {{ item }}"
  when: lookup('vars', item) is undefined
  loop:
    - environment
    - service_name
    
- name: "Validate environment value"
  fail:
    msg: "Invalid environment: {{ environment }}. Must be dev, staging, or prod."
  when: environment not in ['dev', 'staging', 'prod']
```

---

## Runbook Quality Checklist

### Structure Check
- [ ] Metadata section complete (author, date, review cycle)
- [ ] Purpose statement clear (when to use this runbook)
- [ ] Prerequisites listed with specific knowledge requirements
- [ ] Pre-flight checklist with verification commands
- [ ] Variables/parameters documented with examples
- [ ] Procedure has numbered steps with clear objectives
- [ ] Each step has validation checkpoint
- [ ] Rollback procedure for each failure point
- [ ] Error handling section with common errors
- [ ] Changelog tracking changes

### Content Check
- [ ] Steps are granular enough (can be executed without questions)
- [ ] Commands are copy-paste ready (no placeholders without context)
- [ ] Expected outputs are shown (with examples)
- [ ] Rollback triggers are specific (not "if something goes wrong")
- [ ] Error symptoms are descriptive (what you'll see)
- [ ] Validation commands are provided (not just "check that it works")

### Safety Check
- [ ] Pre-flight checklist prevents common failures
- [ ] Rollback procedures are tested and known to work
- [ ] Error escalation path is clear (who to call, when)
- [ ] No destructive steps without verification
- [ ] Secondary service failures don't block primary operation

### Style Check
- [ ] Consistent formatting (commands in code blocks)
- [ ] Operator notes clearly marked (*Note: ...*)
- [ ] Variables use consistent naming (snake_case)
- [ ] Links to related runbooks work
- [ ] Changelog explains why changes were made

---

## Starter Runbook Template

Copy this as the foundation for new runbooks:

```markdown
# Runbook: [Operation Name]

## Metadata
- **Author**: [Your Name]
- **Last Updated**: [YYYY-MM-DD]
- **Review Cycle**: Quarterly
- **Related Runbooks**: [Link 1], [Link 2]

## Purpose
[One paragraph describing what this runbook accomplishes and when to use it]

## Prerequisites

### Knowledge Requirements
- [Required skill 1]
- [Required skill 2]

### Pre-Flight Checklist
- [ ] [Check 1: command and expected result]
- [ ] [Check 2: command and expected result]
- [ ] [Check 3: command and expected result]

## Variables

| Name | Description | Default | Required |
|------|-------------|---------|----------|
| `ENVIRONMENT` | Target environment | None | Yes |
| `SERVICE_NAME` | Service identifier | None | Yes |

## Procedure

### Step 1: [Action]
**Objective**: [What this accomplishes]

**Command**:
```bash
[command with variables]
```

**Validation**:
- [ ] [Check 1 with command]
- [ ] [Check 2 with command]

**Rollback Trigger**: [Specific failure condition]

### Step 2: [Next Action]
...

## Rollback

### If Step [N] Fails
[Specific rollback procedure]

## Post-Procedure

- [ ] [Validation 1]
- [ ] [Validation 2]

## Errors

### Error: [Name]
**Symptoms**: [What you'll see]
**Fix**: [Steps to resolve]

## Changelog

### [Date] - [Author]
- [Change description and reason]
```

---

## Usage Workflow

### Creating a New Runbook

1. **Copy the starter template** above
2. **Fill in metadata** and purpose
3. **List all prerequisites** (be honest about skill requirements)
4. **Create pre-flight checklist** using patterns from your domain
5. **Write procedure steps** with validation after each
6. **Define rollback points** for each major step
7. **Document common errors** you've seen before
8. **Have someone else test it** (dry run without executing)

### Reviewing Someone Else's Runbook

Use the **Runbook Quality Checklist** above. For each item:
- ✅ Pass: Meets standard
- ⚠️ Needs improvement: Fix before approval
- ❌ Missing: Must be added

### For Team Rollout

Share with your team:

> "This is our runbook standard. All operational procedures must follow this structure.
>
> Key principles:
> - Every runbook needs pre-flight checks
> - Every step needs validation
> - Every failure point needs rollback
> - Secondary service failures don't block primary operations
> - Common errors must be documented with fixes"

---

## Cross-Skill Integration

### Inputs (What Triggers Runbook Creation)
| Source Skill | Trigger | Runbook Type |
|---|---|---|
| **architecture-assessor** | Undocumented critical procedure found | Standard operational runbook |
| **architecture-assessor** | Compliance gap in operational procedures | Compliance-enhanced runbook |
| **decision-engine** | ADR creates new operational process | Runbook for new process |
| **terraform-module-scaffold** | Module with lifecycle/migration patterns | Deployment and migration runbook |
| **migration-playbook** | Migration phase requires execution runbook | Migration cutover runbook with rollback procedures |
| Direct request | "Write a runbook for X" | Standard operational runbook |

### Outputs (Where Runbooks Feed)
| Output | Destination Skill | Purpose |
|---|---|---|
| Runbook quality evidence | **architecture-assessor** | Operational maturity score input |
| Escalation procedures | **executive-framer** | Escalation communications use Risk Translation template |
| Incident response procedures | **executive-framer** | SEV-1/SEV-2 communications to leadership |
| Change management compliance | **architecture-assessor** | Regulatory compliance domain checklist evidence |
| Migration runbooks | **migration-playbook** | Execution procedures for each migration phase and batch cutover |

---

## Continuous Improvement

Update patterns as you learn:

- New error cases discovered
- Pre-flight checks that prevented incidents
- Rollback procedures that worked/didn't work
- Validation steps that caught problems early
- Variables that should have been documented

Update this skill as your operational patterns evolve.
