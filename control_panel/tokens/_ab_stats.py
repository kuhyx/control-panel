"""Re-count the A/B arms over a filtered set of assignments.

The all-time verdict is computed by testsAndMisc's ``token_dashboard.ab``;
when the page filters by cwd / model / scope, the arms are recounted here from
its per-assignment ``ab_rows`` with the same statistics (95% Wilson intervals,
Newcombe's hybrid difference interval, normal-approximation means).
"""

from __future__ import annotations

import math
from typing import Any

Z = 1.96
RATES = ("redo", "followup", "error", "correction")


def wilson(k: int, n: int) -> tuple[float, float]:
    """95% Wilson score interval for ``k`` successes in ``n`` trials."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    centre = p + Z * Z / (2 * n)
    spread = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    denom = 1 + Z * Z / n
    return max(0.0, (centre - spread) / denom), min(1.0, (centre + spread) / denom)


def diff_ci(k1: int, n1: int, k2: int, n2: int) -> dict[str, float]:
    """``p1 - p2`` with Newcombe's hybrid-score 95% interval."""
    p1, p2 = (k1 / n1 if n1 else 0.0), (k2 / n2 if n2 else 0.0)
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    diff = p1 - p2
    return {
        "diff": diff,
        "low": diff - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2),
        "high": diff + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2),
    }


def mean_ci(values: list[float]) -> dict[str, float]:
    """Mean with a normal-approximation 95% interval."""
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "low": 0.0, "high": 0.0}
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1) if n > 1 else 0.0
    half = Z * math.sqrt(var / n)
    return {"mean": mean, "low": mean - half, "high": mean + half}


def arm(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """One arm's rates, mean cost / duration and end tags."""
    n = len(rows)
    out: dict[str, Any] = {"n": n}
    for name in RATES:
        k = sum(1 for r in rows if r[name])
        low, high = wilson(k, n)
        out[name] = {"k": k, "rate": k / n if n else None, "low": low, "high": high}
    out["usd"] = mean_ci([r["usd"] for r in rows])
    out["duration_s"] = mean_ci([r["duration_s"] for r in rows])
    tags: dict[str, int] = {}
    for r in rows:
        tags[r["tag"]] = tags.get(r["tag"], 0) + 1
    out["tags"] = tags
    return out


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Both arms and their per-rate differences."""
    arms = {
        name: arm([r for r in rows if r["arm"] == name]) for name in ("sonnet", "opus")
    }
    diffs = {
        name: diff_ci(
            arms["sonnet"][name]["k"],
            arms["sonnet"]["n"],
            arms["opus"][name]["k"],
            arms["opus"]["n"],
        )
        for name in RATES
    }
    return {"arms": arms, "diffs": diffs}
