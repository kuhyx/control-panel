"""Max-plan 5-hour usage windows ("blocks") and their burn.

``python_pkg/token_dashboard/blocks.py`` in testsAndMisc turned out to hold
transcript *content*-block readers, not a window rule, so this uses the
ccusage rule the Max plan's limits are usually tracked with: a block starts
at its first call's hour (floored), lasts 5 hours, and the first call at or
after its end starts the next block.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens._db import ratio

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

BLOCK_S = 5 * 3600
HOUR_S = 3600

_TURNS = (
    "SELECT ts, day, usd FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " ORDER BY ts"
)


def _new(ts: float, day: str) -> dict[str, Any]:
    """An empty block starting at ``ts``'s hour."""
    start = ts - ts % HOUR_S
    return {
        "start": start,
        "end": start + BLOCK_S,
        "day": day,
        "first_ts": ts,
        "last_ts": ts,
        "usd": 0.0,
        "calls": 0,
    }


def blocks(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Every block in the filters, in time order, with $/hour of activity."""
    out: list[dict[str, Any]] = []
    for ts, day, usd in conn.execute(_TURNS, filters.params()):
        if not out or ts >= out[-1]["end"]:
            out.append(_new(ts, day))
        block = out[-1]
        block["last_ts"] = ts
        block["usd"] += usd
        block["calls"] += 1
    for block in out:
        hours = (block["last_ts"] - block["first_ts"]) / HOUR_S
        block["usd_per_hour"] = ratio(block["usd"], hours)
    return out


def daily(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per day (of a block's first call): blocks and the costliest one."""
    days: defaultdict[str, list[float]] = defaultdict(list)
    for row in rows:
        days[row["day"]].append(row["usd"])
    return [
        {"day": day, "blocks": len(usd), "max_block_usd": max(usd)}
        for day, usd in sorted(days.items())
    ]
