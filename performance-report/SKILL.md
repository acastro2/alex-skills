---
name: performance-report
description: Generate a comprehensive 6-month performance report for any Attain Finance engineer. Collects data from GitHub (PRs authored/reviewed, LOC), Azure DevOps (closed stories, story points), and optionally Microsoft 365 (documents, meetings, Teams activity). Produces a self-contained HTML file with charts, tables, categorized work breakdown, and key observations. Use when asked to create a performance report, activity report, or engineer assessment.
triggers:
  - /performance-report
metadata:
  audience: engineering-leadership
  workflow: performance-analysis
---

# Performance Report Skill

This produces an individual's performance material. Treat output as 1:1/manager material: confirm a legitimate purpose before running it on a colleague, and don't share per-person results beyond that purpose.

Generate a data-driven 6-month activity report for any Attain Finance engineer.

## When to Use

- User asks for a performance report, activity report, or engineer assessment
- User provides an email address and wants to understand someone's output
- User triggers `/performance-report`

## Inputs

Ask the user for:
1. **Email address** (required) — e.g., `pavankantipudi@attainfinance.com`
2. **Date range** (optional, default: last 6 months) — e.g., "Dec 2025 to May 2026"
3. **ADO display name** (optional) — will be derived from email if not provided (first + last name from the email prefix)

## Workflow

### Phase 1: Resolve Identity

1. Derive the ADO display name from the email (e.g., `pavankantipudi@...` → "Pavan Kantipudi")
2. Run the GitHub username detection script:
   ```bash
   bash ~/.agents/skills/performance-report/scripts/fetch_github_data.sh "{email}" "{since_date}" "{output_dir}"
   ```
3. If GitHub username not found automatically, ask the user for it.

### Phase 2: Fetch Data

Run both data collection scripts. Use a temporary directory for output:

```bash
OUTPUT_DIR=$(mktemp -d)
```

**GitHub data:**
```bash
bash ~/.agents/skills/performance-report/scripts/fetch_github_data.sh "{email}" "{since_date}" "$OUTPUT_DIR"
```
This produces: `$OUTPUT_DIR/prs_authored.json`, `$OUTPUT_DIR/prs_reviewed.json`

**ADO data:**
```bash
bash ~/.agents/skills/performance-report/scripts/fetch_ado_data.sh "{display_name}" "{since_date}" "$OUTPUT_DIR"
```
This produces: `$OUTPUT_DIR/ado_items.json`

### Phase 3: Verification Gate

**STOP and display a summary before proceeding:**

```
Verification Summary:
  GitHub username: {username}
  Merged PRs found: {count}
  PR reviews found: {count}
  Closed ADO stories found: {count}
  Total story points: {sum}
  Date range: {start} to {end}
  Active orgs: {list}

Proceed with report generation? [Y/n]
```

If counts look wrong (0 PRs for an active engineer, etc.), investigate before proceeding. Common issues:
- Wrong GitHub username
- PAT expired
- Date range mismatch

### Phase 4: M365 Data (Optional)

1. Read the M365 Copilot prompt template:
   ```
   ~/.agents/skills/performance-report/references/m365-copilot-prompt.md
   ```
2. Replace `{{PERSON_NAME}}`, `{{EMAIL}}`, `{{PERIOD_START_LABEL}}`, `{{PERIOD_END_LABEL}}` with actual values
3. Present the prompt to the user and ask them to run it in M365 Copilot Chat
4. Ask: "Do you have M365 Copilot data to include? Paste it here, or type 'skip' to proceed without it."
5. If provided, format it as an HTML section and save to `$OUTPUT_DIR/m365_section.html`

### Phase 5: Categorize Work Items

1. Read the classification prompt template:
   ```
   ~/.agents/skills/performance-report/references/category-classification.md
   ```
2. Read `$OUTPUT_DIR/prs_authored.json` and `$OUTPUT_DIR/ado_items.json`
3. Build the title lists:
   - PRs: `PR:{repo}#{number}: "{title}"` for each PR
   - ADO: `ADO:{id}: "{title}"` for each story
4. Replace `{{PR_TITLES}}` and `{{ADO_TITLES}}` in the prompt template
5. Process the classification yourself (you are the LLM classifier)
6. Output the classification as `$OUTPUT_DIR/categories.json`

**Important classification guidelines:**
- Categories should emerge from the data, not be predetermined
- Support rotation tickets (containing "Team Support", "Tech Support") are always overhead
- Meeting/interview tickets are always overhead
- Triage tickets (same-day open/close, containing "support for", "issue", "fix") are overhead
- Feature work, security hardening, integrations, research are delivery

### Phase 6: Generate Observations

Analyze the collected and categorized data. Write 6-8 factual, unbiased observations as HTML `<li>` elements:

```html
<li><span class="obs-label">Observation title:</span> Factual description with specific numbers and data references.</li>
```

**Observation guidelines:**
- Every observation must cite specific numbers from the data
- Use neutral, factual language — no editorializing
- Include links to specific PRs or ADO items when referencing them
- Cover: code volume, category distribution, delivery/overhead split, initiative progress, collaboration patterns, documentation quality
- If M365 data is available, include observations about meeting leadership and document authorship
- Save as `$OUTPUT_DIR/observations.html`

### Phase 7: Build Report

Run the report builder:

```bash
python3 ~/.agents/skills/performance-report/scripts/build_report.py \
  --prs "$OUTPUT_DIR/prs_authored.json" \
  --reviews "$OUTPUT_DIR/prs_reviewed.json" \
  --ado "$OUTPUT_DIR/ado_items.json" \
  --categories "$OUTPUT_DIR/categories.json" \
  --template ~/.agents/skills/performance-report/references/html-template.html \
  --person-name "{person_name}" \
  --email "{email}" \
  --period-start "{since_date}" \
  --period-end "{end_date}" \
  --output ~/Developer/{slug}-activity-report.html \
  --observations-html "$OUTPUT_DIR/observations.html" \
  --m365-html "$OUTPUT_DIR/m365_section.html"  # only if M365 data was provided
```

The output file goes to `~/Developer/{first_last}-activity-report.html`.

### Phase 8: Verify Report

1. Check the output file exists and is non-empty
2. Verify the file size is reasonable (>200KB, because Chart.js is inlined)
3. Spot-check: PR count in KPI matches the JSON count
4. Spot-check: ADO count in KPI matches the JSON count
5. Report the file path to the user

## Error Handling

| Error | Detection | Recovery |
|-------|-----------|----------|
| `gh` not installed | `which gh` fails | Tell user to install GitHub CLI |
| GitHub auth expired | `gh auth status` fails | Tell user to run `gh auth login` |
| No GitHub username found | Script exits non-zero | Ask user for their GitHub username |
| ADO PAT missing | `$AZURE_DEVOPS_PAT` not set | Tell user to export the PAT |
| ADO PAT expired | HTTP 302 in response | Tell user to regenerate PAT at `https://dev.azure.com/CuroFinTech/_usersSettings/tokens` |
| 0 PRs found | Empty JSON array | Warn user, proceed (may be valid for non-coding role) |
| 0 ADO items found | Empty JSON array | Warn user, proceed (may be valid for new hire) |
| Template not found | FileNotFoundError | Print path and ask user to verify skill installation |
| Python script fails | Non-zero exit | Show stderr, investigate data format issues |

## Output

A single self-contained HTML file (~250KB) that:
- Works offline (Chart.js is inlined)
- Is print-friendly (CSS @media print rules)
- Contains clickable links to all PRs and ADO work items
- Can be shared as a file attachment via Teams or email
