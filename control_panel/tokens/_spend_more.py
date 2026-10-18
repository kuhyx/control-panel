"""Spend breakdown: by month, model, repo, hour x weekday and 5-hour block.

Everything is ``turns.usd`` inside the filters (the plain spend, the same
total the overview shows), cut different ways. Rate-limit errors are the
``api_error`` marks whose name says ``limit``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens import _spend_more_blocks
from control_panel.tokens._db import ratio
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
CUMULATIVE_MONTHS = 3  # the line chart's series: one colour per month
CAPTION = (
    "Spend = the API-call cost inside the filters. Cumulative: running total "
    "within each month (the last three months in range). Heatmap: local "
    "weekday x hour of each call. 5-hour blocks: the ccusage rule -- a block "
    "starts at its first call's hour and lasts 5 hours; $/hour is over the "
    "time between its first and last call. The plan's real window is "
    "account-wide, so a cwd/model/scope filter shows only that slice of each "
    "block. Rate limits: API errors named rate_limit (or another *limit*)."
)

_MONTHS = (
    "SELECT substr(day, 1, 7), SUM(usd), COUNT(*) FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY 1 ORDER BY 1 DESC"
)
_DAYS = (
    "SELECT day, SUM(usd) FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY day ORDER BY day"
)
_BY_MODEL = (
    "SELECT model, SUM(usd), COUNT(*) FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY model ORDER BY SUM(usd) DESC"
)
_BY_CWD = (
    "SELECT cwd, SUM(usd), COUNT(*) FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY cwd ORDER BY SUM(usd) DESC"
)
_HEATMAP = (
    "SELECT CAST(strftime('%w', ts, 'unixepoch', 'localtime') AS INT),"
    " CAST(strftime('%H', ts, 'unixepoch', 'localtime') AS INT),"
    " SUM(usd), COUNT(*) FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY 1, 2"
)
_RATE_LIMITS = (
    "SELECT day, SUM(count) FROM marks WHERE kind = 'api_error'"
    " AND name LIKE '%limit%' AND"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY day ORDER BY day"
)


def _cumulative(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Running total within each of the last months, per day of month."""
    days = conn.execute(_DAYS, filters.params()).fetchall()
    months = sorted({day[:7] for day, _ in days})[-CUMULATIVE_MONTHS:]
    totals: defaultdict[str, float] = defaultdict(float)
    rows = []
    for day, usd in days:
        if day[:7] in months:
            totals[day[:7]] += usd
            rows.append(
                {
                    "month": day[:7],
                    "dom": int(day[8:10]),
                    "usd": usd,
                    "cum_usd": totals[day[:7]],
                }
            )
    return rows


def _shares(
    rows: list[tuple[Any, ...]], label: str, total: float
) -> list[dict[str, Any]]:
    """(label, usd, calls) rows with each one's share of the total."""
    return [
        {label: name, "usd": usd, "calls": calls, "share": ratio(usd, total)}
        for name, usd, calls in rows
    ]


def _heatmap(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Spend per local weekday (0 = Monday) x hour, the costliest first."""
    cells = [
        {"weekday": (sunday_first + 6) % 7, "hour": hour, "usd": usd, "calls": n}
        for sunday_first, hour, usd, n in conn.execute(_HEATMAP, filters.params())
    ]
    return sorted(cells, key=lambda c: -c["usd"])


TABLES = (
    "months",
    "by_model",
    "by_cwd",
    "heatmap",
    "blocks",
    "block_daily",
    "rate_limits",
)


@panel(
    "spend_more",
    "Spend breakdown",
    order=72,
    tables={
        **{t: {"limit": str(TOP)} for t in TABLES},
        "blocks": {"limit": str(TOP), "sort": "-usd"},
        "cumulative": {"limit": "0"},
    },
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Spend by month, model, repo, hour x weekday, 5-hour block, limits."""
    months = [
        {"month": m, "usd": usd, "calls": n}
        for m, usd, n in conn.execute(_MONTHS, filters.params())
    ]
    total = sum(m["usd"] for m in months)
    blocks = _spend_more_blocks.blocks(conn, filters)
    return {
        "caption": CAPTION,
        "totals": {"usd": total, "blocks": len(blocks)},
        "months": months,
        "cumulative": _cumulative(conn, filters),
        "by_model": _shares(
            conn.execute(_BY_MODEL, filters.params()).fetchall(), "model", total
        ),
        "by_cwd": _shares(
            conn.execute(_BY_CWD, filters.params()).fetchall(), "cwd", total
        ),
        "heatmap": _heatmap(conn, filters),
        "blocks": blocks,
        "block_daily": _spend_more_blocks.daily(blocks),
        "rate_limits": [
            {"day": day, "errors": n}
            for day, n in conn.execute(_RATE_LIMITS, filters.params())
        ],
    }
