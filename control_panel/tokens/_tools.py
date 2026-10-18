"""Tools: how each tool and command family behaves, fails and repeats.

Per tool name and per family (``git status``, ``mcp:<server>``, ...): calls,
error rate, result-size percentiles and the failure kinds the user or the
harness caused (rejected / denied / hook). Time-cap kills come from two
places: calls the ingester marked ``time_cap``, and the time-cap hook's own
log (``events`` rows from source ``time-cap``) -- kept apart, never summed.
"""

from __future__ import annotations

from collections import defaultdict
import math
from typing import TYPE_CHECKING, Any

from control_panel.tokens._db import day_of, ratio
from control_panel.tokens._registry import panel
from control_panel.tokens._tools_loops import CAPTION as LOOP_CAPTION
from control_panel.tokens._tools_loops import loops

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
FAILED = ("rejected", "denied", "hook")
CAPTION = (
    "Error rate = calls whose result was an error / calls. Result p50 / p95 "
    "= the median and 95th-percentile result size in tokens (estimated at 4 "
    "chars/token). rejected = the user said no, denied = a permission rule, "
    "hook = a hook blocked it. Time-cap kills: calls marked time_cap, and the "
    "time-cap hook's log (events: killed_* / denied / unmatched); the log has "
    "no cwd, model or scope, so it shows only when those filters are off. "
    + LOOP_CAPTION
)

_CALLS = (
    "SELECT name, family, result_tokens, is_error, error_kind FROM calls WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
)
_BATCHING = (
    "SELECT day, COUNT(*), SUM(batch > 1) FROM calls WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " GROUP BY day ORDER BY day"
)
_EVENTS = "SELECT ts, kind FROM events WHERE source = 'time-cap' AND ts BETWEEN ? AND ?"


def percentile(values: list[int], share: float) -> int | None:
    """Nearest-rank percentile of ``values`` (``None`` when empty)."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(share * len(ordered)) - 1)]


class _Tally:
    """Calls, errors, result sizes and error kinds for one tool or family."""

    def __init__(self) -> None:
        """Start empty."""
        self.sizes: list[int] = []
        self.errors = 0
        self.kinds: defaultdict[str, int] = defaultdict(int)

    def add(self, tokens: int, is_error: int, kind: str) -> None:
        """Count one call."""
        self.sizes.append(tokens or 0)
        self.errors += int(bool(is_error))
        self.kinds[kind] += 1

    def row(self) -> dict[str, Any]:
        """The table row's numbers."""
        calls = len(self.sizes)
        return {
            "calls": calls,
            "errors": self.errors,
            "error_rate": ratio(self.errors, calls),
            "result_p50": percentile(self.sizes, 0.5),
            "result_p95": percentile(self.sizes, 0.95),
            **{kind: self.kinds[kind] for kind in FAILED},
            "time_cap": self.kinds["time_cap"],
        }


def _tallies(
    conn: sqlite3.Connection, filters: Filters
) -> tuple[dict[str, _Tally], dict[str, _Tally], _Tally]:
    """Tallies by tool name, by family, and overall."""
    names: defaultdict[str, _Tally] = defaultdict(_Tally)
    families: defaultdict[str, _Tally] = defaultdict(_Tally)
    total = _Tally()
    for name, family, tokens, is_error, kind in conn.execute(_CALLS, filters.params()):
        for tally in (names[name], families[family], total):
            tally.add(tokens, is_error, kind or "")
    return names, families, total


def _ranked(tallies: dict[str, _Tally], label: str) -> list[dict[str, Any]]:
    """Rows for a table, the most-called first."""
    rows = [{label: key, **t.row()} for key, t in tallies.items()]
    return sorted(rows, key=lambda r: (-r["calls"], r[label]))


def _events_apply(filters: Filters) -> bool:
    """The time-cap log has only a timestamp: no cwd/model/scope filter."""
    return not filters.cwd and not filters.model and filters.scope == "all"


def _time_cap(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Time-cap log rows per day and kind (empty when it cannot be filtered)."""
    if not _events_apply(filters):
        return []
    counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    for ts, kind in conn.execute(_EVENTS, (filters.since, filters.until)):
        counts[day_of(ts), kind] += 1
    rows = [{"day": d, "kind": k, "count": n} for (d, k), n in counts.items()]
    rows.sort(key=lambda r: r["kind"])
    return sorted(rows, key=lambda r: r["day"], reverse=True)


def _event_totals(
    rows: list[dict[str, Any]], filters: Filters
) -> dict[str, int] | None:
    """Kills / denials / unmatched from the log, ``None`` when filtered out."""
    if not _events_apply(filters):
        return None
    out = {"killed": 0, "denied": 0, "unmatched": 0}
    for row in rows:
        bucket = "killed" if row["kind"].startswith("killed") else row["kind"]
        out[bucket] += row["count"]
    return out


TABLES = ("tools", "families", "loops", "time_cap", "batching")


@panel("tools", "Tools", order=70, tables={t: {"limit": str(TOP)} for t in TABLES})
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Per-tool and per-family behaviour, loops, time-cap kills, batching."""
    names, families, total = _tallies(conn, filters)
    batching = [
        {"day": day, "calls": n, "batched": b, "share": ratio(b, n)}
        for day, n, b in conn.execute(_BATCHING, filters.params())
    ]
    time_cap = _time_cap(conn, filters)
    summary = total.row()
    batched = sum(d["batched"] for d in batching)
    return {
        "caption": CAPTION,
        "totals": {
            "calls": summary["calls"],
            "errors": summary["errors"],
            "error_rate": summary["error_rate"],
            "failed": {kind: summary[kind] for kind in FAILED},
            "time_cap_calls": summary["time_cap"],
            "time_cap_events": _event_totals(time_cap, filters),
            "batched_share": ratio(batched, summary["calls"]),
        },
        "tools": _ranked(names, "name"),
        "families": _ranked(families, "family"),
        "loops": loops(conn, filters),
        "time_cap": time_cap,
        "batching": batching,
    }
