"""Pure rules behind the Anomalies panel: spend spikes and call categories.

Kept apart from the queries so each rule is one small, testable function.
The categories follow session-autopsy's: waiting on something (polling),
checking the work (lint-test) and version control (vcs).
"""

from __future__ import annotations

from datetime import date, timedelta
import re
from statistics import median
from typing import Any

TRAILING_DAYS = 7
SPIKE_FACTOR = 2.0
POLLING = frozenset({"sleep", "watch", "until", "while", "timeout", "monitor"})
LINT_TEST = frozenset(
    {
        "pytest",
        "vitest",
        "jest",
        "eslint",
        "ruff",
        "mypy",
        "pylint",
        "pre-commit",
        "shellcheck",
        "prettier",
        "tsc",
        "lint",
        "test",
        "check",
        "analyze",
        "coverage",
    }
)
_WORDS = re.compile(r"[^\w.-]+")


def category(family: str) -> str | None:
    """Polling / lint-test / vcs for a call family, ``None`` for the rest."""
    words = [w for w in _WORDS.split(family.lower()) if w]
    if not words:
        return None
    if words[0] in POLLING or "poll" in family.lower():
        return "polling"
    if LINT_TEST.intersection(words):
        return "lint-test"
    if words[0] == "git":
        return "vcs"
    return None


def _days(first: str, last: str) -> list[str]:
    """Every calendar day from ``first`` to ``last``, inclusive."""
    start, end = date.fromisoformat(first), date.fromisoformat(last)
    return [
        (start + timedelta(days=n)).isoformat() for n in range((end - start).days + 1)
    ]


def spikes(daily: dict[str, float], start: str, last: str) -> list[dict[str, Any]]:
    """Days in ``start..last`` spending over 2x the trailing 7-day median.

    ``daily`` must hold spend from seven days before ``start`` too, so the
    first days in range have a full trailing window. Days without spend count
    as $0. A $0 median flags nothing: after an idle week every day would.
    """
    first = (date.fromisoformat(start) - timedelta(days=TRAILING_DAYS)).isoformat()
    days = _days(first, last)
    usd = [daily.get(day, 0.0) for day in days]
    rows = []
    for at in range(TRAILING_DAYS, len(days)):
        mid = median(usd[at - TRAILING_DAYS : at])
        if mid > 0 and usd[at] > SPIKE_FACTOR * mid:
            rows.append(
                {
                    "day": days[at],
                    "usd": usd[at],
                    "median_usd": mid,
                    "ratio": usd[at] / mid,
                }
            )
    return sorted(rows, key=lambda r: -r["ratio"])
