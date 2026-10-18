"""Levers panel: every lever's status and outcome, and its metric over time.

A lever's metric is charted from two sources: the token_audit snapshots (the
values the ledger is scored against) and, where the metric can be recomputed
from stored turns, a rolling 7-day series so the move around the applied date
is visible between snapshots.
"""

from __future__ import annotations

from collections import deque
from dataclasses import replace
import json
from typing import TYPE_CHECKING, Any

from control_panel.tokens import _db, _overview
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    from collections.abc import Callable
    import sqlite3

    from control_panel.tokens._db import Filters

ROLLING_DAYS = 7
# Daily sums are (usd, calls, sub, opus, over, home); each metric is a ratio.
Sums = tuple[float, ...]
RECOMPUTABLE: dict[str, Callable[[Sums], float | None]] = {
    "usd_per_day": lambda s: s[0] / ROLLING_DAYS,
    "calls_per_day": lambda s: s[1] / ROLLING_DAYS,
    "usd_per_call": lambda s: _db.ratio(s[0], s[1]),
    "subagent_usd_share": lambda s: _db.ratio(s[2], s[0]),
    "opus_usd_share": lambda s: _db.ratio(s[3], s[0]),
    "over_budget_usd_share": lambda s: _db.ratio(s[4], s[0]),
    "home_cwd_usd_share": lambda s: _db.ratio(s[5], s[0]),
}
_FIELDS = (
    "source",
    "date",
    "lever",
    "metric",
    "baseline",
    "predicted",
    "actual",
    "lower_is_better",
    "status",
    "outcome",
    "detail",
)


def _rolling(rows: list[Any], metric: str) -> list[dict[str, Any]]:
    """Trailing 7-row sums turned into the metric, one point per day."""
    fn = RECOMPUTABLE[metric]
    window: deque[Sums] = deque(maxlen=ROLLING_DAYS)
    out = []
    for day, *sums in rows:
        window.append(tuple(float(v) for v in sums))
        total = tuple(sum(col) for col in zip(*window, strict=True))
        out.append({"date": day, "value": fn(total)})
    return out


def _snapshots(conn: sqlite3.Connection) -> list[tuple[str, dict[str, Any]]]:
    """``(date, metrics)`` per snapshot, oldest first."""
    return [
        (name[:10], json.loads(metrics or "{}"))
        for name, metrics in conn.execute(
            "SELECT name, metrics FROM snapshots ORDER BY name"
        )
    ]


@panel("levers", "Levers", order=40)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Lever rows plus, per metric, snapshot points and a rolling series."""
    rows = [
        dict(zip(_FIELDS, r, strict=True))
        for r in conn.execute(
            "SELECT source, date, lever, metric, baseline, predicted, actual,"
            " lower_is_better, status, outcome, detail FROM levers"
        )
    ]
    everything = replace(filters, since=0.0)
    daily = _overview.daily_rows(conn, everything, _db.home())
    snaps = _snapshots(conn)
    series: dict[str, Any] = {}
    for metric in sorted({r["metric"] for r in rows if r["metric"]}):
        series[metric] = {
            "snapshots": [
                {"date": day, "value": m[metric]} for day, m in snaps if metric in m
            ],
            "daily": _rolling(daily, metric) if metric in RECOMPUTABLE else [],
        }
    return {"rows": rows, "series": series, "rolling_days": ROLLING_DAYS}
