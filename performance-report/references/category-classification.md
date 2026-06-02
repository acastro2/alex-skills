# Category Classification Prompt

You are classifying work items (GitHub PRs and Azure DevOps stories) for a performance report. Read all titles and derive natural categories that best describe this person's work.

## Rules

1. Derive 5-8 categories from the data. Categories should reflect the actual work themes, not be generic.
2. Each item gets exactly one category.
3. Mark each category as either "delivery" (feature work, architecture, research, security, infrastructure) or "overhead" (support rotations, triage, meetings, admin, maintenance).
4. An "Other" category is acceptable but should contain <10% of items.
5. Use short category names (1-3 words).

## Tag Color Mapping

Map each category to one of these CSS class suffixes: `summit`, `security`, `borrowell`, `identity`, `cicd`, `support`, `triage`, `research`, `meetings`, `mobile`, `docs`. If no existing class fits, use `triage` as a neutral default.

## Output Format

Return valid JSON:

```json
{
  "categories": ["Category A", "Category B", ...],
  "overhead_categories": ["Category X", "Category Y"],
  "tag_colors": {
    "Category A": "summit",
    "Category B": "security"
  },
  "assignments": {
    "PR:RepoName#123": "Category A",
    "ADO:45678": "Category B"
  }
}
```

## Key Format for Assignments

- GitHub PRs: `PR:{repo_name}#{pr_number}` (e.g., `PR:SummitAPI#1809`)
- ADO stories: `ADO:{work_item_id}` (e.g., `ADO:245249`)

## Few-Shot Example

Given these PR titles:
- SummitAPI#1799: "RSA changes"
- Web#6305: "CSP set on server side for applications"
- AffiliateLeads#103: "add borrowell changes"
- SummitAPI#1786: "Install asdf in action-validate workflow"

And these ADO titles:
- 246600: "Team Support Echo Bravo & Charlie - Sprint 01/14-01/27"
- 248247: "Lead Engineer interview"
- 246441: "Explore open source Identity server (OpenIddict)"
- 247454: "Investigate Dot818 leads not generating in Summit"

Derived categories:
```json
{
  "categories": ["Summit Platform", "Security", "Borrowell", "Identity Server", "CI/CD", "Team Support", "Meetings", "Triage"],
  "overhead_categories": ["Team Support", "Meetings", "Triage"],
  "tag_colors": {
    "Summit Platform": "summit",
    "Security": "security",
    "Borrowell": "borrowell",
    "Identity Server": "identity",
    "CI/CD": "cicd",
    "Team Support": "support",
    "Meetings": "meetings",
    "Triage": "triage"
  },
  "assignments": {
    "PR:SummitAPI#1799": "Security",
    "PR:Web#6305": "Security",
    "PR:AffiliateLeads#103": "Borrowell",
    "PR:SummitAPI#1786": "CI/CD",
    "ADO:246600": "Team Support",
    "ADO:248247": "Meetings",
    "ADO:246441": "Identity Server",
    "ADO:247454": "Summit Platform"
  }
}
```

## Input Data

**Merged PRs:**
{{PR_TITLES}}

**Closed ADO Stories:**
{{ADO_TITLES}}
