"""Cost per user prompt: what one message to Claude ends up costing.

``prompt_summary`` holds, per user prompt, the main thread's own spend
(``usd_own``) and the spend of the subagents it spawned (``usd_sub``). A
prompt belongs to the filters when it was sent inside the date range and
its session has at least one API call matching cwd, model and scope; the
scope then picks the side of its cost (main: own, sub: subagents, all: both).
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from statistics import mean, median
from typing import TYPE_CHECKING, Any

from control_panel.tokens import _db
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
TOP_SHARE = 10  # the "top 10 prompts' share of the spend" tile
# Histogram bucket lower edges (USD) and labels; the last bucket is open.
BUCKETS = (
    (0.0, "< $0.10"),
    (0.1, "$0.10-0.50"),
    (0.5, "$0.50-1"),
    (1.0, "$1-2"),
    (2.0, "$2-5"),
    (5.0, "$5-10"),
    (10.0, "$10-20"),
    (20.0, "≥ $20"),
)
EDGES = [low for low, _ in BUCKETS]
FILTERED_BY = (
    "date range on the prompt's time; cwd, model and scope on its session's"
    " API calls (any match); the scope also picks the cost side"
)
CAPTION = (
    "USD per user prompt = the main thread's spend until the next prompt"
    " (usd_own) plus the subagents it spawned (usd_sub); scope main shows"
    " usd_own, sub shows usd_sub (only prompts that spawned subagents), all"
    " shows both. A prompt is in when its session has any API call matching"
    " cwd/model/scope -- its cost is not split by model, so a model filter"
    " picks prompts, not dollars. Compaction and hook bounces count toward"
    " the prompt they happened under."
)

_SESSIONS = (
    "SELECT DISTINCT main_key FROM turns WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
)
_PROMPTS = (
    "SELECT key, idx, ts, text, usd_own, usd_sub, active_s, calls"
    " FROM prompt_summary WHERE ts BETWEEN ? AND ? ORDER BY ts"
)


def _cost(scope: str, own: float, sub: float) -> float:
    """The prompt's cost on the scope's side."""
    return {"main": own, "sub": sub}.get(scope, own + sub)


def _prompts(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Prompts in the filters, costliest first."""
    sessions = {key for (key,) in conn.execute(_SESSIONS, filters.params())}
    rows = []
    for key, idx, ts, text, raw_own, raw_sub, active, calls in conn.execute(
        _PROMPTS, (filters.since, filters.until)
    ):
        own, sub = raw_own or 0.0, raw_sub or 0.0
        if key not in sessions or (filters.scope == "sub" and sub <= 0):
            continue
        rows.append(
            {
                "ts": ts,
                "key": key,
                "idx": idx,
                "text": text or "",
                "usd_own": own,
                "usd_sub": sub,
                "usd": _cost(filters.scope, own, sub),
                "total": own + sub,
                "active_s": active,
                "calls": calls,
            }
        )
    return sorted(rows, key=lambda r: (-r["usd"], r["ts"]))


def _daily(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per day: prompts, their median and mean cost, and the sum."""
    days: defaultdict[str, list[float]] = defaultdict(list)
    for row in rows:
        days[_db.day_of(row["ts"])].append(row["usd"])
    return [
        {
            "day": day,
            "prompts": len(costs),
            "median_usd": median(costs),
            "mean_usd": mean(costs),
            "usd": sum(costs),
        }
        for day, costs in sorted(days.items())
    ]


def _histogram(costs: list[float]) -> list[dict[str, Any]]:
    """How many prompts fall in each cost bucket (every bucket listed)."""
    counts = [0] * len(BUCKETS)
    for cost in costs:
        counts[max(0, bisect_right(EDGES, cost) - 1)] += 1
    return [
        {"bucket": label, "prompts": n}
        for (_, label), n in zip(BUCKETS, counts, strict=True)
    ]


@panel("prompts", "Cost per prompt", order=82, tables={"prompts": {"limit": str(TOP)}})
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """USD per user prompt: daily median/mean, histogram, costliest prompts."""
    rows = _prompts(conn, filters)
    costs = [r["usd"] for r in rows]
    total = sum(costs)
    return {
        "caption": CAPTION,
        "filtered_by": FILTERED_BY,
        "totals": {
            "prompts": len(rows),
            "usd": total,
            "median_usd": median(costs) if costs else None,
            "mean_usd": mean(costs) if costs else None,
            "top10_share": _db.ratio(sum(costs[:TOP_SHARE]), total),
        },
        "daily": _daily(rows),
        "histogram": _histogram(costs),
        "prompts": rows,
    }
