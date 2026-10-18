"""Anomalies: the spend that stands out -- spikes, big sessions, loops.

Read by the token-dashboard MCP client (``GET /api/tokens/panel/anomalies``)
as well as the page. ``over`` (query parameter, default $20) is the session
cost above which a session is listed as expensive.
"""

from __future__ import annotations

from collections import defaultdict
import dataclasses
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

from control_panel.tokens._anomalies_tokens_rules import TRAILING_DAYS, category, spikes
from control_panel.tokens._db import day_of
from control_panel.tokens._registry import panel
from control_panel.tokens._tools_loops import CAPTION as LOOP_CAPTION
from control_panel.tokens._tools_loops import loops

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
OVER = 20.0
DAY_S = 86400
CAPTION = (
    "Spikes: days spending more than 2x the median of the 7 days before "
    "(days without spend count as $0; a $0 median flags nothing). Expensive: "
    "sessions (main transcript + subagents, inside the filters) over the "
    "`over` query parameter (default $20). Categories: calls by family -- "
    "polling (sleep / until / while / watch / Monitor), lint-test (pytest, "
    "vitest, eslint, ruff, pre-commit, ... lint / test / check), vcs (git *) "
    "-- with their context cost (creation + carry). " + LOOP_CAPTION
)

_DAILY = (
    "SELECT day, SUM(usd) FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY day"
)
_SESSIONS = (
    "SELECT main_key, MIN(day), SUM(usd), COUNT(*) FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY main_key HAVING SUM(usd) > ? ORDER BY SUM(usd) DESC"
)
_FAMILIES = (
    "SELECT main_key, family, COUNT(*), SUM(create_usd + carry_usd)"
    " FROM calls WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY main_key, family"
)
_SUMMARY = "SELECT key, title, cwd FROM session_summary"


def over_of(filters: Filters) -> float:
    """The ``over`` query parameter (dollars), :data:`OVER` when unusable."""
    raw = parse_qs(filters.query).get("over", [""])[0]
    try:
        return max(0.0, float(raw))
    except ValueError:
        return OVER


def _spikes(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Spend spikes inside the range, judged against the week before it."""
    early = dataclasses.replace(filters, since=filters.since - TRAILING_DAYS * DAY_S)
    daily = dict(conn.execute(_DAILY, early.params()).fetchall())
    return spikes(daily, day_of(filters.since), day_of(filters.until))


def _expensive(
    conn: sqlite3.Connection, filters: Filters, over: float
) -> list[dict[str, Any]]:
    """Sessions costing more than ``over`` inside the filters."""
    summary = {key: (title, cwd) for key, title, cwd in conn.execute(_SUMMARY)}
    return [
        {
            "key": key,
            "title": summary.get(key, ("", ""))[0] or "",
            "cwd": summary.get(key, ("", ""))[1] or "",
            "day": day,
            "usd": usd,
            "calls": calls,
        }
        for key, day, usd, calls in conn.execute(_SESSIONS, (*filters.params(), over))
    ]


def _categories(
    conn: sqlite3.Connection, filters: Filters
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Per session and category, then per category: calls and context cost."""
    cells: defaultdict[tuple[str, str], list[float]] = defaultdict(lambda: [0, 0.0])
    for key, family, calls, cost in conn.execute(_FAMILIES, filters.params()):
        kind = category(family or "")
        if kind is not None:
            cells[key, kind][0] += calls
            cells[key, kind][1] += cost or 0.0
    rows: list[dict[str, Any]] = [
        {"key": key, "category": kind, "calls": int(n), "cost_usd": usd}
        for (key, kind), (n, usd) in cells.items()
    ]
    rows.sort(key=lambda r: (-r["cost_usd"], r["key"]))
    totals: defaultdict[str, list[float]] = defaultdict(lambda: [0, 0.0])
    for row in rows:
        totals[row["category"]][0] += row["calls"]
        totals[row["category"]][1] += row["cost_usd"]
    summary = [
        {"category": kind, "calls": int(n), "cost_usd": usd}
        for kind, (n, usd) in sorted(totals.items(), key=lambda t: -t[1][1])
    ]
    return rows, summary


TABLES = ("spikes", "expensive", "loops", "categories", "category_totals")


@panel(
    "anomalies",
    "Anomalies",
    order=86,
    tables={t: {"limit": str(TOP)} for t in TABLES},
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Spend spikes, expensive sessions, runaway loops, call categories."""
    over = over_of(filters)
    categories, category_totals = _categories(conn, filters)
    return {
        "caption": CAPTION,
        "over": over,
        "spikes": _spikes(conn, filters),
        "expensive": _expensive(conn, filters, over),
        "loops": loops(conn, filters),
        "categories": categories,
        "category_totals": category_totals,
    }
