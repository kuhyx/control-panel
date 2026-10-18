"""Errors: API errors, rate/usage-limit hits, interruptions and failing tool calls.

API errors and interruptions are ``marks`` rows (kind ``api_error``: name =
the error type, detail = its message; kind ``interrupt``), aggregated per
prompt so ``count`` is the number of events. Tool errors are ``calls`` rows
with ``is_error = 1`` and an ``error_kind`` (exit_code / tool_error /
rejected / denied / hook / time_cap / interrupted / error). Error rates are
errors over *all* calls of the same group, so a rarely used tool that fails
once reads as a high rate: compare with its call count.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
RATE_LIMIT = "rate_limit"
CAPTION = (
    "API errors as the transcript logged them (rate_limit covers both the "
    "per-minute rate limit and the plan's session/usage limit; the detail "
    "says which). Interrupts = turns the user stopped. Tool error rate = "
    "failing calls / all calls of that tool or kind in the filter; a "
    "non-zero exit code counts as an error even when it was expected "
    "(grep with no match, a red test run)."
)

_API_TYPES = (
    "SELECT name, SUM(count), COUNT(DISTINCT main_key), MAX(ts) FROM marks WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " AND kind = 'api_error' GROUP BY name ORDER BY SUM(count) DESC, name"
)
_API_DETAIL = (
    "SELECT name, detail, SUM(count), MAX(ts) FROM marks WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " AND kind = 'api_error' GROUP BY name, detail"
    " ORDER BY SUM(count) DESC, MAX(ts) DESC"
)
_MARK_DAYS = (
    "SELECT day,"
    " SUM(CASE WHEN kind = 'api_error' THEN count ELSE 0 END),"
    " SUM(CASE WHEN kind = 'api_error' AND name = ? THEN count ELSE 0 END),"
    " SUM(CASE WHEN kind = 'interrupt' THEN count ELSE 0 END)"
    " FROM marks WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " AND kind IN ('api_error', 'interrupt') GROUP BY day"
)
_CALL_DAYS = (
    "SELECT day, COUNT(*), SUM(is_error) FROM calls WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " GROUP BY day"
)
_KINDS = (
    "SELECT error_kind, COUNT(*) FROM calls WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " AND is_error = 1 GROUP BY error_kind ORDER BY COUNT(*) DESC, error_kind"
)
_TOOLS = (
    "SELECT name, family, COUNT(*), SUM(is_error) FROM calls WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " GROUP BY name, family HAVING SUM(is_error) > 0"
    " ORDER BY SUM(is_error) DESC, COUNT(*) DESC, name, family"
)
_RECENT = (
    "SELECT ts, key, name, family, target, error_kind FROM calls WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " AND is_error = 1 ORDER BY ts DESC"
)
RECENT_COLUMNS = ("ts", "key", "name", "family", "target", "error_kind")


def _rate(errors: int, calls: int) -> float | None:
    """Errors over calls (None when there were no calls)."""
    return errors / calls if calls else None


def _daily(conn: sqlite3.Connection, params: tuple[object, ...]) -> list[Any]:
    """Per day: API errors, rate-limit hits, interrupts, calls and tool errors."""
    days: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: dict.fromkeys(
            ("api_errors", "rate_limits", "interrupts", "calls", "tool_errors"), 0
        )
    )
    for day, api, limits, interrupts in conn.execute(_MARK_DAYS, (RATE_LIMIT, *params)):
        days[day].update(api_errors=api, rate_limits=limits, interrupts=interrupts)
    for day, calls, errors in conn.execute(_CALL_DAYS, params):
        days[day].update(calls=calls, tool_errors=errors)
    return [
        {"day": day, **v, "error_rate": _rate(v["tool_errors"], v["calls"])}
        for day, v in sorted(days.items())
    ]


def _tools(conn: sqlite3.Connection, params: tuple[object, ...]) -> list[Any]:
    """Failing tools / command families with their error rate."""
    return [
        {
            "name": name,
            "family": family,
            "calls": calls,
            "errors": errors,
            "error_rate": errors / calls,
        }
        for name, family, calls, errors in conn.execute(_TOOLS, params)
    ]


def _totals(daily: list[dict[str, Any]], types: list[dict[str, Any]]) -> dict[str, Any]:
    """Tile numbers: API errors, rate-limit hits, interrupts, tool error rate."""
    limit = next((t for t in types if t["type"] == RATE_LIMIT), None)
    calls = sum(d["calls"] for d in daily)
    errors = sum(d["tool_errors"] for d in daily)
    return {
        "api_errors": sum(t["count"] for t in types),
        "rate_limit_hits": limit["count"] if limit else 0,
        "rate_limit_sessions": limit["sessions"] if limit else 0,
        "last_rate_limit_ts": limit["last_ts"] if limit else None,
        "interrupts": sum(d["interrupts"] for d in daily),
        "calls": calls,
        "tool_errors": errors,
        "error_rate": _rate(errors, calls),
    }


TABLES = ("api_error_types", "api_errors", "error_kinds", "error_tools", "recent")


@panel("errors", "Errors", order=88, tables={t: {"limit": str(TOP)} for t in TABLES})
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """API errors, limits, interrupts and tool errors, per type and per day."""
    params = filters.params()
    types = [
        {"type": name, "count": count, "sessions": sessions, "last_ts": last}
        for name, count, sessions, last in conn.execute(_API_TYPES, params)
    ]
    daily = _daily(conn, params)
    totals = _totals(daily, types)
    kinds = [
        {
            "error_kind": kind,
            "count": count,
            "share": count / totals["tool_errors"],
            "rate": count / totals["calls"],
        }
        for kind, count in conn.execute(_KINDS, params)
    ]
    return {
        "caption": CAPTION,
        "totals": totals,
        "daily": daily,
        "api_error_types": types,
        "api_errors": [
            {"type": name, "detail": detail, "count": count, "last_ts": last}
            for name, detail, count, last in conn.execute(_API_DETAIL, params)
        ],
        "error_kinds": kinds,
        "error_tools": _tools(conn, params),
        "recent": [
            dict(zip(RECENT_COLUMNS, row, strict=True))
            for row in conn.execute(_RECENT, params)
        ],
    }
