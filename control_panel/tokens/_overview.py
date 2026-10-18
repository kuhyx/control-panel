"""Spend panel: stat tiles, daily and weekly series, aggregate-only history."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens import _db
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

DAY_S = 86400.0
MIN_SPAN_S = 60.0
# Over-budget means context > 300,000 (token_audit.breakdown.CONTEXT_BUDGET);
# inlined in the SQL literal below.

_DAILY = (
    "SELECT day, SUM(usd), COUNT(*),"
    " SUM(CASE WHEN is_sub = 1 THEN usd ELSE 0 END),"
    " SUM(CASE WHEN model LIKE '%opus%' THEN usd ELSE 0 END),"
    " SUM(CASE WHEN context > 300000 THEN usd ELSE 0 END),"
    " SUM(CASE WHEN cwd = ? THEN usd ELSE 0 END)"
    " FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY day ORDER BY day"
)
_SPAN = (
    "SELECT MIN(ts), MAX(ts) FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
)


def daily_rows(conn: sqlite3.Connection, filters: Filters, home: str) -> list[Any]:
    """Raw per-day sums: day, usd, calls, sub, opus, over-budget, home-cwd."""
    return conn.execute(_DAILY, (home, *filters.params())).fetchall()


def _aggregate(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Autopsy-only sessions (transcript gone), calibrated, per day."""
    factor = float(_db.meta(conn, "autopsy_calibration") or 1.0)
    rows = conn.execute(
        "SELECT day, COUNT(*), SUM(usd_est) FROM aggregate_sessions"
        " WHERE started BETWEEN ? AND ? AND session_id NOT IN"
        " (SELECT key FROM session_summary)"
        " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
        " GROUP BY day ORDER BY day",
        (filters.since, filters.until, filters.cwd, filters.cwd, filters.cwd),
    ).fetchall()
    return [
        {"day": day, "sessions": n, "usd_est": round(usd * factor, 2)}
        for day, n, usd in rows
    ]


def _series(rows: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Daily rows with their ratios, and the same rolled up per week."""
    daily: list[dict[str, Any]] = []
    weekly: defaultdict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for day, usd, calls, sub, opus, over, at_home in rows:
        daily.append(
            {
                "day": day,
                "usd": usd,
                "calls": calls,
                "usd_per_call": _db.ratio(usd, calls),
                "sub_share": _db.ratio(sub, usd),
                "opus_share": _db.ratio(opus, usd),
                "over_share": _db.ratio(over, usd),
                "home_share": _db.ratio(at_home, usd),
            }
        )
        weekly[_db.monday(day)][0] += usd
        weekly[_db.monday(day)][1] += calls
    weeks = [
        {"week": week, "usd": sums[0], "calls": int(sums[1])}
        for week, sums in sorted(weekly.items())
    ]
    return daily, weeks


def _tiles(
    conn: sqlite3.Connection, filters: Filters, daily: list[dict[str, Any]]
) -> dict[str, Any]:
    """Headline numbers; USD/day is over the record span, like token_audit."""
    first, last = conn.execute(_SPAN, filters.params()).fetchone()
    total = sum(d["usd"] for d in daily)
    calls = sum(d["calls"] for d in daily)
    span_days = max((last or 0) - (first or 0), MIN_SPAN_S) / DAY_S
    active = conn.execute(
        "SELECT SUM(active_s), COUNT(*) FROM session_summary"
        " WHERE first_ts BETWEEN ? AND ?",
        (filters.since, filters.until),
    ).fetchone()
    return {
        "usd": total,
        "calls": calls,
        "usd_per_day": total / span_days if calls else 0.0,
        "usd_per_call": _db.ratio(total, calls),
        "active_h": (active[0] or 0) / 3600,
        "sessions": active[1],
    }


@panel("overview", "Spend", order=10)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Tiles, daily/weekly series and history the store cannot detail."""
    daily, weekly = _series(daily_rows(conn, filters, _db.home()))
    prompts = conn.execute(
        "SELECT day, prompts FROM prompt_activity WHERE day BETWEEN ? AND ?"
        " ORDER BY day",
        (_db.day_of(filters.since), _db.day_of(filters.until)),
    ).fetchall()
    return {
        "tiles": _tiles(conn, filters, daily),
        "daily": daily,
        "weekly": weekly,
        "aggregate": _aggregate(conn, filters),
        "prompts": [{"day": d, "prompts": n} for d, n in prompts],
    }
