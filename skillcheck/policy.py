"""Facts about this repo that a rule cannot infer from the text.

Three kinds of fact live here, and only three. All are repo-wide on purpose: a skill folder
copied out of the repo should not carry an exemption it no longer needs, and a rule that had
to read 34 private configs would be a rule nobody can review.

`path_bases` -- directories a skill legitimately points into but does not own: another
skill, the vendored trees, Alex's own tool configs. A base that no longer exists is a
finding, so a stale entry fails loudly instead of quietly excusing a dead path.

`external_paths` -- exact spans that are real but live off this machine: the Attain repos
are not cloned here and the work OneDrive is not mounted. Exact spans, never prefixes, so
the exemption cannot hide a new broken path. Each entry names where the file is.

`standalone` -- reference files written to be read on their own, so the same warning or
navigation line must appear in more than one of them. Without this, `duplicate-sentences`
flags correct prose, and a rule that cries wolf is a rule that gets ignored.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Policy:
    path_bases: tuple[str, ...] = ()
    external_paths: frozenset[str] = frozenset()
    standalone: frozenset[str] = frozenset()

    @classmethod
    def for_skill(cls, name: str) -> Policy:
        return POLICY.get(name, cls())


POLICY: dict[str, Policy] = {
    # each register is loaded alone when writing in that register, so the shared "never
    # invent a fact" rules must appear in more than one of them.
    "alex-voice": Policy(
        standalone=frozenset(
            {
                "references/registers/chat.md",
                "references/registers/comms.md",
                "references/registers/docs.md",
                "references/registers/exec.md",
                "references/registers/spoken.md",
            }
        ),
    ),
    # archeologist points at the m365 CLI reference, which lives in the m365 skill, and
    # ships its Jev gates as a reference loaded alone.
    "archeologist": Policy(
        path_bases=("../m365",),
        standalone=frozenset({"references/jev-gates.md"}),
    ),
    # a work artifact in the Attain IT portfolio repo; not cloned on this machine.
    "ado-ticket-writer": Policy(
        external_paths=frozenset(
            {"docs/knowledge/information-technology/request-model.md"}
        ),
    ),
    # screenshots' evidence JSONs live in the Attain IT portfolio repo, off this machine.
    "browser-apple-events": Policy(
        external_paths=frozenset(
            {
                "information-technology/evidence/it-states-v2-ui-2026-09-09/request-rejection-255270.json",
                "information-technology/evidence/it-states-v2-ui-2026-09-09/normal-submission-readiness-defect.json",
            }
        ),
    ),
    # the exa references are three separate API calls and each stands alone, so all three
    # must carry the same wording about the curl blocks being for Pi.
    "search": Policy(
        standalone=frozenset(
            {
                "references/exa-agent.md",
                "references/exa-contents.md",
                "references/exa-search.md",
            }
        ),
    ),
    # the two source references are read alone, so each repeats the hand-off to the shared
    # Summary and write step.
    "scribe": Policy(
        standalone=frozenset({"references/teams.md", "references/hidock.md"}),
    ),
    # skill-creator's prose talks about the vendored creators' own trees.
    "skill-creator": Policy(path_bases=("vendor/codex", "vendor/claude")),
}
