#!/usr/bin/env python3
"""
Git Change Analyzer - Extract intent from git diffs and commits

Analyzes git history to understand what changed and why, then
extracts structured information for Azure DevOps work item creation.
"""

import subprocess
import re
import json
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class ChangeIntent:
    """Structured representation of change intent"""
    action: str  # Added, Fixed, Refactored, Removed, Updated
    target: str  # What was changed
    motivation: str  # Why it was done
    impact: str  # What changes for users
    scope: str  # Component/service affected
    commits: List[str]  # Related commit messages
    files_changed: List[str]  # Files that were modified


def run_git_command(cmd: List[str]) -> str:
    """Execute git command and return output"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"Error: {e.stderr}", file=sys.stderr)
        return ""


def get_commits_in_branch(base_branch: str = "main") -> List[str]:
    """Get list of commits in current branch not in base branch"""
    cmd = ["git", "log", f"{base_branch}..HEAD", "--oneline", "--no-merges"]
    output = run_git_command(cmd)
    if not output:
        return []

    commits = []
    for line in output.split("\n"):
        if line.strip():
            # Format: "hash message"
            parts = line.split(" ", 1)
            if len(parts) == 2:
                commits.append(parts[1])

    return commits


def get_changed_files(base_branch: str = "main") -> List[str]:
    """Get list of files changed in current branch"""
    cmd = ["git", "diff", f"{base_branch}..HEAD", "--name-only"]
    output = run_git_command(cmd)
    return [f.strip() for f in output.split("\n") if f.strip()]


def parse_conventional_commit(message: str) -> Dict[str, str]:
    """Parse conventional commit format"""
    # Pattern: type(scope): subject
    pattern = r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?: (?P<subject>.+)$"
    match = re.match(pattern, message)

    if match:
        return {
            "type": match.group("type"),
            "scope": match.group("scope") or "",
            "subject": match.group("subject")
        }

    return {"type": "", "scope": "", "subject": message}


def determine_action(commit_type: str) -> str:
    """Map commit type to action verb"""
    action_map = {
        "feat": "Added",
        "feature": "Added",
        "add": "Added",
        "fix": "Fixed",
        "bugfix": "Fixed",
        "refactor": "Refactored",
        "remove": "Removed",
        "delete": "Removed",
        "update": "Updated",
        "docs": "Documented",
        "test": "Tested",
        "chore": "Updated",
        "perf": "Optimized",
        "security": "Secured"
    }
    return action_map.get(commit_type.lower(), "Modified")


def analyze_changes(base_branch: str = "main") -> ChangeIntent:
    """Analyze git changes and extract intent"""
    commits = get_commits_in_branch(base_branch)
    files = get_changed_files(base_branch)

    if not commits:
        return ChangeIntent(
            action="Unknown",
            target="Unknown",
            motivation="No changes detected",
            impact="None",
            scope="Unknown",
            commits=[],
            files_changed=files
        )

    # Analyze first commit (usually the main one)
    first_commit = commits[0]
    parsed = parse_conventional_commit(first_commit)

    action = determine_action(parsed["type"])
    scope = parsed["scope"] or infer_scope_from_files(files)
    target = parsed["subject"]

    # Infer motivation from commit body or files
    motivation = infer_motivation(commits, files)

    # Infer impact from action and target
    impact = infer_impact(action, target, files)

    return ChangeIntent(
        action=action,
        target=target,
        motivation=motivation,
        impact=impact,
        scope=scope,
        commits=commits,
        files_changed=files
    )


def infer_scope_from_files(files: List[str]) -> str:
    """Infer component scope from changed files"""
    if not files:
        return "Unknown"

    # Extract directory names
    dirs = set()
    for f in files:
        parts = f.split("/")
        if len(parts) > 1:
            dirs.add(parts[0])

    if dirs:
        return ", ".join(sorted(dirs))

    return "General"


def infer_motivation(commits: List[str], files: List[str]) -> str:
    """Infer motivation from commits and files"""
    # Look for keywords in commits
    motivation_keywords = {
        "fix": "to resolve an issue",
        "bug": "to fix a bug",
        "feat": "to add new functionality",
        "add": "to add new capability",
        "update": "to improve existing functionality",
        "refactor": "to improve code quality",
        "security": "to address security concerns",
        "perf": "to improve performance"
    }

    for commit in commits:
        lower_commit = commit.lower()
        for keyword, motivation in motivation_keywords.items():
            if keyword in lower_commit:
                return motivation

    # Default based on file types
    if any("test" in f.lower() for f in files):
        return "to improve test coverage"
    if any("doc" in f.lower() for f in files):
        return "to improve documentation"

    return "to implement required changes"


def infer_impact(action: str, target: str, files: List[str]) -> str:
    """Infer user impact from changes"""
    if action in ["Added", "Implemented"]:
        return f"Users can now {target.lower()}"
    elif action == "Fixed":
        return f"Users no longer experience issues with {target.lower()}"
    elif action == "Refactored":
        return f"System is more maintainable with improved {target.lower()}"
    elif action == "Optimized":
        return f"Users experience better performance in {target.lower()}"
    else:
        return f"Changes to {target.lower()} are now in effect"


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze git changes and extract intent for Azure DevOps work items"
    )
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch to compare against (default: main)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    intent = analyze_changes(args.base_branch)

    if args.json:
        print(json.dumps(asdict(intent), indent=2))
    else:
        print(f"Action: {intent.action}")
        print(f"Target: {intent.target}")
        print(f"Scope: {intent.scope}")
        print(f"Motivation: {intent.motivation}")
        print(f"Impact: {intent.impact}")
        print(f"\nCommits ({len(intent.commits)}):")
        for commit in intent.commits:
            print(f"  - {commit}")
        print(f"\nFiles changed ({len(intent.files_changed)}):")
        for f in intent.files_changed[:10]:  # Show first 10
            print(f"  - {f}")
        if len(intent.files_changed) > 10:
            print(f"  ... and {len(intent.files_changed) - 10} more")


if __name__ == "__main__":
    main()
