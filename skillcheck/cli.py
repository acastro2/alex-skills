"""The command the gate calls.

    python -m skillcheck              # every skill in the repo
    python -m skillcheck path/to/skill
    python -m skillcheck --list-rules

Exit codes follow the rule the rest of the repo uses for a check: 0 clean, 1 findings,
2 the checker itself could not run. A finding is one line, `file:line - rule - message`,
because that is what an editor and a CI log can both read without parsing anything.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .core import RULES, check_repo, check_skill, discover_skills

REPO_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None, root: Path = REPO_ROOT) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if "--list-rules" in args:
        for rule in RULES:
            print(f"{rule.id}\t{rule.why}")
        return 0

    targets = [Path(arg) for arg in args if not arg.startswith("-")]
    try:
        if targets:
            findings = []
            for target in targets:
                findings.extend(check_skill(target, root=root))
        else:
            findings = check_repo(root)
    except RuntimeError as error:
        print(f"skillcheck: {error}", file=sys.stderr)
        return 2

    for finding in findings:
        print(finding.text())
    if findings:
        print(f"\n{len(findings)} finding(s) in {len({f.skill for f in findings})} skill(s)")
        return 1

    checked = len(targets) or len(discover_skills(root))
    print(f"Checked {checked} skills: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
