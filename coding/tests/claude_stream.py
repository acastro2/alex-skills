"""Parse `claude -p --output-format stream-json --verbose` lines."""
import json


def _events(lines):
    for line in lines:
        try:
            e = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(e, dict):
            yield e


def skills_invoked(lines) -> list[str]:
    """Skill names from Skill tool_use blocks in assistant events, in order, raw."""
    out = []
    for e in _events(lines):
        if e.get("type") != "assistant":
            continue
        msg = e.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Skill":
                inp = b.get("input")
                if isinstance(inp, dict) and isinstance(inp.get("skill"), str):
                    out.append(inp["skill"])
    return out


def final_result(lines) -> dict:
    """The last result event, or {}."""
    res = {}
    for e in _events(lines):
        if e.get("type") == "result":
            res = e
    return res


def triggered(skills, name) -> bool:
    return any(s == name or s.startswith(name + ":") for s in skills)
