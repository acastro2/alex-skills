# Upstream clones live outside this repo

The pinned upstream repos (see `../UPSTREAM.md` for SHAs) are pulled
locally OUTSIDE every skill root, so no skill loader registers their
nested SKILL.md files, and they are never committed here. On the VM the
location is `~/.agents/skill-refs/personal-finance/`.

Pull (or re-pull) commands, matching the pins as of 2026-10-21:

```bash
REF=~/.agents/skill-refs/personal-finance
mkdir -p "$REF" && cd "$REF"

# homeCFO (full clone)
git clone --depth 1 https://github.com/bn-wright/homecfo homecfo

# Personal Finance Coach (sparse: the one skill folder only)
git clone --depth 1 --filter=blob:none --sparse https://github.com/curiositech/some_claude_skills some_claude_skills
git -C some_claude_skills sparse-checkout set .claude/skills/personal-finance-coach

# Retirement Planner (sparse: the plugin only)
git clone --depth 1 --filter=blob:none --sparse https://github.com/mrelph/claude-agents-skills claude-agents-skills
git -C claude-agents-skills sparse-checkout set plugins/retirement-planner

# InvestSkill (sparse: the us-stock-analysis plugin only)
git clone --depth 1 --filter=blob:none --sparse https://github.com/yennanliu/InvestSkill InvestSkill
git -C InvestSkill sparse-checkout set plugins/us-stock-analysis
```

After pulling, check out the pinned commit from `../UPSTREAM.md` before
consulting a file, and follow the refresh protocol there before moving
any pin.
