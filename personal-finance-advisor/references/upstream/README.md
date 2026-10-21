# Upstream clones live outside this repo

The pinned upstream repos (see `../UPSTREAM.md` for SHAs) are pulled
locally OUTSIDE every skill root, so no skill loader registers their
nested SKILL.md files, and they are never committed here. On the VM the
location is `~/.agents/skill-refs/personal-finance/`.

Pull each pin with `fetch_pin.sh` (next to this file). A plain
`git clone --depth 1` checks out upstream HEAD, which equals the pin
only on the day it is recorded; `fetch_pin.sh` fetches the exact SHA,
detaches at it, and fails loudly if HEAD does not match.

```bash
REF=~/.agents/skill-refs/personal-finance
./fetch_pin.sh "$REF/homecfo"              https://github.com/bn-wright/homecfo               245ab494889d667ff2b4fbc7266cd6a750b27734
./fetch_pin.sh "$REF/some_claude_skills"   https://github.com/curiositech/some_claude_skills  6713fc7a6451c8dee5903b98cd2063ff4cbf7317 .claude/skills/personal-finance-coach
./fetch_pin.sh "$REF/claude-agents-skills" https://github.com/mrelph/claude-agents-skills     7f8396fd01dd79b1c2fd38d72e7827a12a8b4467 plugins/retirement-planner
./fetch_pin.sh "$REF/InvestSkill"          https://github.com/yennanliu/InvestSkill           d9a37b3ee0201995d8079e89956ff4524d283ebc plugins/us-stock-analysis
```

Run the commands from this directory so `./fetch_pin.sh` resolves. To
move a pin, follow the refresh protocol in `../UPSTREAM.md`.
