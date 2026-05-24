# alex-skills

A collection of skills for Claude Code and opencode — modular instruction packs that give AI agents domain-specific expertise, voice guidelines, and tooling.

## Install

```bash
git clone https://github.com/acastro2/alex-skills.git ~/.agents/skills
```

This puts each skill at `~/.agents/skills/<name>/SKILL.md`, which opencode discovers automatically.

Skills are also discoverable from `~/.config/opencode/skills/` and `~/.claude/skills/` — see [opencode skills docs](https://opencode.ai/docs/skills/).

## What's in here

Each top-level directory is a self-contained skill with its own `SKILL.md` entry point, optional scripts, references, and assets.

| Skill | What it does |
|---|---|
| `ado-ticket-writer` | Write Azure DevOps work items |
| `agent-browser` | Browse and interact with web pages |
| `agent-creator` | Create new Claude Code agents |
| `architecture-assessor` | Assess and review system architectures |
| `attain-github-archive` | Archive GitHub repos for Attain |
| `blog-reviewer` | Review blog posts against Alex's voice |
| `blog-reviewer-mentor` | Review mentoring/career blog posts |
| `code-simplifier` | Simplify and refactor code |
| `comms-writer` | Write internal communications |
| `decision-engine` | Structure and analyze decisions |
| `design-md` | Generate design system documentation |
| `dev-to-publisher` | Publish posts to Dev.to |
| `docs-reviewer` | Review documentation |
| `docs-writer` | Write documentation |
| `docx` | Generate Word documents |
| `executive-framer` | Frame content for executive audiences |
| `explorer` | Explore and search codebases |
| `frontend-design` | Design and build frontend components |
| `internal-comms` | Write internal communications |
| `lucid-diagrammer` | Create Lucidchart diagrams |
| `mcp-builder` | Build MCP servers |
| `migration-playbook` | Create migration playbooks |
| `playwright-cli` | Run Playwright browser tests from CLI |
| `pptx` | Generate PowerPoint presentations |
| `pr-reviewer` | Review pull requests |
| `readiness-report` | Generate readiness reports |
| `runbook-generator` | Generate operational runbooks |
| `sharepoint` | Manage SharePoint pages |
| `skill-creator` | Create and iterate on new skills |
| `terraform-module-scaffold` | Scaffold Terraform modules |
| `test-generator` | Generate test suites |
| `uncodixfy` | Deglorify corporate jargon |
| `vendor-evaluator` | Evaluate vendors and tools |
| `webapp-testing` | Test web applications |

### Shared resources

- `shared/alex-voice-core.md` — Alex's writing voice (core)
- `shared/alex-voice-blog.md` — Alex's voice for blog posts
- `shared/alex-voice-comms.md` — Alex's voice for comms
- `shared/alex-voice-docs.md` — Alex's voice for docs

## Skill anatomy

```
skill-name/
├── SKILL.md        # Entry point (YAML frontmatter + instructions)
├── scripts/        # Executable helpers
├── references/    # Docs loaded into context as needed
├── assets/         # Templates, icons, fonts
├── agents/         # Subagent instructions
├── evals/          # Test prompts and assertions
└── LICENSE.txt     # Per-skill license
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).