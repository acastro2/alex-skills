#!/usr/bin/env python3
"""Retired AX write experiment. Kept to reject old commands without browser access."""

import argparse
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--allow-test-windows", action="store_true")
    parser.add_argument("--browser-owner-coordinated", action="store_true")
    args = parser.parse_args()
    if not args.allow_test_windows or not args.browser_owner_coordinated:
        parser.error("Need disposable-window approval AND browser-owner coordination. These flags record them, not grant them.")
    print(json.dumps({"ok": False, "error": {"code": "AX_WRITES_DISABLED",
        "message": "The AX write experiment was dropped. This runner does not open a browser or start servers.",
        "outcome": "not_started"}}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
