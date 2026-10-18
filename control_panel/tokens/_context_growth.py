"""Context size: how big each call's prompt is, and how sessions grow.

``turns.context`` is the call's whole prompt (input + cache write + cache
read tokens). Every call re-sends it, so a session past 250k-300k pays for
that bulk on every turn until it compacts or hands off. A key is one
session or one subagent: each has its own context.
"""

from __future__ import annotations

from collections import defaultdict
import math
from typing import TYPE_CHECKING, Any

from control_panel.tokens._context_growth_handoffs import handoffs
from control_panel.tokens._context_growth_stats import bucket, percentiles
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
GROWTH_KEYS = 10  # sessions (by spend) whose growth curve is drawn
MAX_POINTS = 120  # points per curve; longer sessions are thinned
PER_CHART = 3  # curves per chart (the three-colour categorical palette)
EDGES = (0, 50_000, 100_000, 150_000, 200_000, 250_000, 300_000)
LABELS = ("0-50k", "50-100k", "100-150k", "150-200k", "200-250k", "250-300k")
HIGH, HIGHER = 250_000, 300_000
CAPTION = (
    "Context = the call's whole prompt (input + cache write + cache read "
    "tokens), re-sent on every call. Percentiles are nearest-rank over every "
    "call in range. Growth curves: the 10 keys (sessions or subagents) with the "
    "most spend, context by call index, three per chart (curves longer than "
    "120 calls are sampled every n-th call, n shared within a chart, plus the "
    "last call). Crossings: keys with a call over 250k; "
    "'$ over 300k' is the whole cost of those calls. Handoffs: Write calls to a "
    "path containing 'handoff', prompts mentioning one (usually picking it up) "
    "and hook marks naming one; handoffs written outside a tool call are missed."
)

_CALLS = (
    "SELECT key, main_key, context, usd FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " ORDER BY key, ts"
)
_TITLES = "SELECT key, title FROM session_summary"


def thin(contexts: list[int], longest: int) -> list[dict[str, int]]:
    """One curve's points on its chart's shared grid, plus its last call.

    The grid's stride comes from the chart's ``longest`` curve, so every
    curve drawn together is sampled at the same call indices (the chart
    spaces x by rank, so differing grids would warp the shorter curves).
    """
    stride = max(1, math.ceil(longest / MAX_POINTS))
    points = [
        {"call": index + 1, "context": contexts[index]}
        for index in range(0, len(contexts), stride)
    ]
    if points[-1]["call"] != len(contexts):
        points.append({"call": len(contexts), "context": contexts[-1]})
    return points


def curves(
    dearest: list[dict[str, Any]], series: dict[str, list[int]]
) -> list[dict[str, Any]]:
    """Growth curves, :data:`PER_CHART` per chart, each chart on one grid."""
    out = []
    for start in range(0, len(dearest), PER_CHART):
        group = dearest[start : start + PER_CHART]
        longest = max(len(series[r["key"]]) for r in group)
        out += [
            {
                "chart": start // PER_CHART + 1,
                "key": r["key"],
                "title": r["title"],
                "usd": r["usd"],
                "max_context": r["max_context"],
                "points": thin(series[r["key"]], longest),
            }
            for r in group
        ]
    return out


def _histogram(contexts: list[int], usds: list[float]) -> list[dict[str, Any]]:
    """Calls and their cost per 50k bucket, the last one open-ended."""
    labels = (*LABELS, f"{HIGHER // 1000}k+")
    calls, cost = [0] * len(labels), [0.0] * len(labels)
    for value, usd in zip(contexts, usds, strict=True):
        index = bucket(value, EDGES)
        calls[index] += 1
        cost[index] += usd
    return [
        {"bucket": label, "calls": calls[i], "usd": cost[i]}
        for i, label in enumerate(labels)
    ]


def _crossing(key: str, title: str, calls: list[tuple[int, float]]) -> dict[str, Any]:
    """One key's time over 250k / 300k."""
    return {
        "key": key,
        "title": title,
        "max_context": max(c for c, _ in calls),
        "calls": len(calls),
        "calls_over_250k": sum(1 for c, _ in calls if c > HIGH),
        "calls_over_300k": sum(1 for c, _ in calls if c > HIGHER),
        "usd_over_300k": sum(u for c, u in calls if c > HIGHER),
        "usd": sum(u for _, u in calls),
    }


@panel(
    "context_growth",
    "Context size",
    order=68,
    tables={"crossings": {"limit": str(TOP)}, "handoffs": {"limit": str(TOP)}},
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Context distribution, growth curves, 250k/300k crossings, handoffs."""
    titles = dict(conn.execute(_TITLES).fetchall())
    keys: defaultdict[str, list[tuple[int, float]]] = defaultdict(list)
    mains: dict[str, str] = {}
    for key, main, context, usd in conn.execute(_CALLS, filters.params()):
        keys[key].append((context, usd))
        mains[key] = main
    contexts = [c for calls in keys.values() for c, _ in calls]
    usds = [u for calls in keys.values() for _, u in calls]
    rows = [
        _crossing(k, titles.get(mains[k]) or "", calls) for k, calls in keys.items()
    ]
    dearest = sorted(rows, key=lambda r: (-r["usd"], r["key"]))[:GROWTH_KEYS]
    return {
        "caption": CAPTION,
        "percentiles": percentiles(contexts, (0.5, 0.9, 0.99)),
        "histogram": _histogram(contexts, usds),
        "growth": curves(
            dearest, {r["key"]: [c for c, _ in keys[r["key"]]] for r in dearest}
        ),
        "crossings": sorted(
            (r for r in rows if r["calls_over_250k"]),
            key=lambda r: (-r["usd_over_300k"], -r["max_context"]),
        ),
        "handoffs": handoffs(conn, filters),
    }
