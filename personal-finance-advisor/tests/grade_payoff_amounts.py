#!/usr/bin/env python3
"""Grade eval 4 (windfall vs deferred-interest cliff) on amounts, not strings.

A correct answer allocates the promo bucket's full shortfall (400) to the
promo first and the remainder (1,600) to the high-APR card, in either
currency notation. Usage:
    python3 grade_payoff_amounts.py <response.txt>
    python3 grade_payoff_amounts.py --self-test
Exits 0 on PASS, 1 on FAIL.
"""

import re
import sys

SHORTFALL = re.compile(r"(?:\$|USD\s?)400\b")
REMAINDER = re.compile(r"(?:\$|USD\s?)1,?600\b")


def grade(text: str) -> list[str]:
    failures = []
    if not SHORTFALL.search(text):
        failures.append("shortfall amount 400 not found (promo must be funded in full)")
    if not REMAINDER.search(text):
        failures.append("remainder amount 1,600 not found (rest goes to the high-APR card)")
    return failures


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        good = "Send USD 400 to the promo to clear it, then $1,600 to the 29.99% card."
        bad = "Put the whole USD 2,000 toward the 29.99% card."
        assert grade(good) == [], grade(good)
        assert grade(bad) != []
        print("self-test PASS")
        return 0
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    failures = grade(open(sys.argv[1]).read())
    for failure in failures:
        print(f"FAIL: {failure}")
    print("PASS" if not failures else "FAIL")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
