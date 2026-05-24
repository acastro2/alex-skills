#!/usr/bin/env python3
"""
HTML Builder — emit Azure DevOps work item description HTML in the PARCH-6 shape.

ADO `System.Description` and `Microsoft.VSTS.Common.AcceptanceCriteria` are HTML.
This builder renders the 6-section template from structured Python data,
escaping user-provided strings, and returns an HTML string ready to drop into
a JSON Patch payload.
"""

from __future__ import annotations

import argparse
import html
import json
from typing import Iterable, Mapping, Sequence


def escape(text: str) -> str:
    """Escape a string for safe inclusion in HTML body text."""
    return html.escape(text, quote=True)


def _h3(title: str) -> str:
    return f"<h3>{escape(title)}</h3>"


def _p(text: str) -> str:
    return f"<p>{text}</p>"


def _strong(label: str, value: str | None = None) -> str:
    if value is None:
        return f"<strong>{escape(label)}</strong>"
    return f"<strong>{escape(label)}:</strong> {escape(value)}"


def _ul(items: Iterable[str]) -> str:
    body = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"<ul>{body}</ul>"


def _ul_html(items: Iterable[str]) -> str:
    """Bullet list where items are already HTML (not escaped)."""
    body = "".join(f"<li>{item}</li>" for item in items)
    return f"<ul>{body}</ul>"


def _code_block(code: str) -> str:
    return f"<pre><code>{escape(code)}</code></pre>"


def build_acceptance_criteria_html(items: Sequence[str]) -> str:
    """Build the value for Microsoft.VSTS.Common.AcceptanceCriteria."""
    if not items:
        return ""
    return _ul(items)


def build_parch6(
    *,
    objective: str,
    acceptance_criteria: Sequence[str],
    constraints: Sequence[str] | None = None,
    security: str | None = None,
    timing: str | None = None,
    technical: Mapping[str, Sequence[str]] | None = None,
    schema: str | None = None,
    flow: Mapping[str, str] | None = None,
    validation: Sequence[tuple[str, str]] | None = None,
    resources: Mapping[str, str] | None = None,
) -> str:
    """Render a complete PARCH-6 description as HTML.

    Args:
        objective: One-sentence end-state summary.
        acceptance_criteria: List of Given/When/Then strings.
        constraints: Optional list of "DO NOT" constraints.
        security: Optional security/compliance note.
        timing: Optional timing/SLA note.
        technical: Mapping of subsection title -> list of bullet points
            (e.g. {"Configuration & Connectivity": ["endpoint: ..."]}).
        schema: Optional JSON/code block for data schema.
        flow: Mapping of phase name -> description
            (e.g. {"Phase 1 (Preparation)": "..."}).
        validation: List of (action, expected_result) tuples.
        resources: Mapping of resource label -> URL or text.

    Returns:
        A single HTML string ready for System.Description.
    """
    parts: list[str] = []

    parts.append(_h3("1. Constitutional Intent & Success Criteria"))
    parts.append(_p("<em>The \"North Star\" and testable reality of completed work.</em>"))
    parts.append(_p(_strong("Objective", objective)))
    if acceptance_criteria:
        parts.append(_p(_strong("Acceptance Criteria (Given/When/Then)")))
        parts.append(_ul(acceptance_criteria))

    parts.append(_h3("2. Constraints & Guardrails"))
    parts.append(_p("<em>Operational boundaries. Read before implementation.</em>"))
    if constraints:
        parts.append(_p(_strong("Critical Non-Actions")))
        parts.append(_ul(constraints))
    if security:
        parts.append(_p(_strong("Security & Compliance", security)))
    if timing:
        parts.append(_p(_strong("Timing/SLA", timing)))

    parts.append(_h3("3. Technical Interface (The Contract)"))
    parts.append(_p("<em>Immutable technical facts for implementation.</em>"))
    if technical:
        for subsection, bullets in technical.items():
            parts.append(_p(_strong(subsection)))
            parts.append(_ul(bullets))
    if schema:
        parts.append(_p(_strong("Data Schema")))
        parts.append(_code_block(schema))

    parts.append(_h3("4. Logic & Implementation Flow"))
    parts.append(_p("<em>The execution algorithm for humans.</em>"))
    if flow:
        for phase, body in flow.items():
            parts.append(_p(_strong(phase, body)))

    parts.append(_h3("5. Validation Steps"))
    parts.append(_p("<em>How to verify the contract was fulfilled.</em>"))
    if validation:
        for action, expected in validation:
            parts.append(_p(_strong("Action", action)))
            parts.append(_p(_strong("Expected Result", expected)))

    parts.append(_h3("6. Resources & Team Context"))
    if resources:
        for label, value in resources.items():
            if value.startswith(("http://", "https://")):
                anchor = f'<a href="{escape(value)}">{escape(value)}</a>'
                parts.append(f"<p>{_strong(label)}: {anchor}</p>")
            else:
                parts.append(_p(_strong(label, value)))

    return "".join(parts)


def build_json_patch(
    *,
    title: str,
    description_html: str,
    area_path: str,
    iteration_path: str,
    acceptance_criteria_html: str | None = None,
    tags: Sequence[str] | None = None,
    priority: int | None = None,
) -> list[dict]:
    """Build a JSON Patch document for ADO work item create."""
    patch: list[dict] = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": description_html},
        {"op": "add", "path": "/fields/System.AreaPath", "value": area_path},
        {"op": "add", "path": "/fields/System.IterationPath", "value": iteration_path},
    ]
    if acceptance_criteria_html:
        patch.append({
            "op": "add",
            "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
            "value": acceptance_criteria_html,
        })
    if tags:
        patch.append({
            "op": "add",
            "path": "/fields/System.Tags",
            "value": "; ".join(tags),
        })
    if priority is not None:
        patch.append({
            "op": "add",
            "path": "/fields/Microsoft.VSTS.Common.Priority",
            "value": priority,
        })
    return patch


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ADO PARCH-6 HTML / JSON Patch")
    parser.add_argument("--example", action="store_true", help="Print example HTML and JSON Patch")
    parser.add_argument("--patch", action="store_true", help="With --example, print full JSON Patch")
    args = parser.parse_args()

    if not args.example:
        parser.print_help()
        return

    description_html = build_parch6(
        objective="Users can authenticate via Google OAuth2 and have their profile synced.",
        acceptance_criteria=[
            "Given user is logged out, When they click \"Sign in with Google\", Then OAuth flow initiates",
            "Given OAuth completes successfully, When user returns to app, Then profile is synced from Google",
        ],
        constraints=[
            "DO NOT: Store Google access tokens in plain text",
            "DO NOT: Modify existing email/password authentication flow",
        ],
        security="All tokens encrypted at rest (AES-256). PII handling per company policy.",
        timing="OAuth callback must complete within 5s p95.",
        technical={
            "Configuration & Connectivity": [
                "Callback: POST /auth/google/callback",
                "Env: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET",
                "Scopes: openid profile email",
            ],
        },
        schema='{"google_id": "string", "email": "string"}',
        flow={
            "Phase 1 (Preparation)": "Register OAuth client in Google Cloud, store credentials in vault.",
            "Phase 2 (Execution)": "Implement /auth/google/start, callback handler, token exchange, profile sync.",
            "Phase 3 (Finalization)": "Add login button, write integration tests, deploy behind feature flag.",
        },
        validation=[
            ("Run npm run test:integration -- auth/google", "All tests pass"),
            ("Manually click Google login button", "Successful redirect, session cookie set, user row created"),
        ],
        resources={
            "Runbook": "https://wiki/runbooks/oauth",
            "Infrastructure Source": "https://github.com/CuroFinTech/echo",
            "Support Channel": "#echo-team",
        },
    )

    ac_html = build_acceptance_criteria_html([
        "Given user is logged out, When they click \"Sign in with Google\", Then OAuth flow initiates",
        "Given OAuth completes successfully, When user returns to app, Then profile is synced from Google",
    ])

    if args.patch:
        patch = build_json_patch(
            title="[ECHO] Enable OAuth2 Google authentication for users",
            description_html=description_html,
            acceptance_criteria_html=ac_html,
            area_path="Tiger\\Echo",
            iteration_path="Tiger",
            tags=["auth", "oauth2"],
            priority=2,
        )
        print(json.dumps(patch, indent=2))
    else:
        print(description_html)


if __name__ == "__main__":
    main()
