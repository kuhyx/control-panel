"""Task-size estimator: its call estimates against what sessions really did.

The task-size hook estimates, from a session's first prompt, how many API
calls the task will take (``estimates``: session id -> ``est_calls``). Here
each estimate meets the session's real calls under the filters. Separately,
every time a session hit the context gate anyway, ``task_size_miss.py``
logged why the estimator failed to prevent it (``events``, source
``task-size-miss``; kinds split-ignored, predicted-fits, not-estimated,
resumed, skipped:<status>). Those rows carry no session, cwd or model.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import TYPE_CHECKING, Any

from control_panel.tokens import _db
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
OVER, UNDER = 2.0, 0.5  # a miss: actual > 2x the estimate, or < 0.5x
SOURCE = "task-size-miss"
FILTERED_BY = (
    "sessions: date, cwd, model and scope (on their API calls);"
    " gate-miss events: date range only (they carry no session, cwd or model)"
)
CAPTION = (
    "Estimate = the task-size hook's est_calls from the first prompt; actual"
    " = the session's API calls under the filters (subagents' calls count"
    " toward their parent session). A miss is actual > 2x the estimate (over)"
    " or < 0.5x (under); within 2x is the hit rate; a 0 estimate has no"
    " ratio and counts as over. The estimator was tuned"
    " on main-thread calls only, so scope=main is the like-for-like reading;"
    " a date range that cuts a session counts only its calls inside the"
    " range, and estimates whose session has no calls in range are left out."
    " Gate misses: sessions that reached the context gate anyway, by why the"
    " estimator did not stop them (predicted-fits is its real error)."
)

_SESSIONS = (
    "SELECT e.session_id, e.est_calls, COUNT(*), SUM(usd), MIN(ts), MIN(cwd)"
    " FROM estimates e JOIN turns ON main_key = e.session_id WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " GROUP BY e.session_id"
)
_TITLES = "SELECT key, title FROM session_summary"
_EVENTS = (
    "SELECT ts, kind, detail FROM events"
    " WHERE source = ? AND ts BETWEEN ? AND ? ORDER BY ts"
)


def _miss(est: int, actual: int) -> str:
    """``over``, ``under`` or ``""`` (within 2x) for one session."""
    if actual > OVER * est:
        return "over"
    return "under" if actual < UNDER * est else ""


def _spread(row: dict[str, Any]) -> float:
    """How far off the estimate was, either way (``inf`` for a 0 estimate)."""
    ratio = row["ratio"]
    return float("inf") if ratio is None else max(ratio, 1 / ratio)


def _sessions(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Estimated sessions with calls in range, worst misses first."""
    titles = dict(conn.execute(_TITLES))
    rows = [
        {
            "session_id": key,
            "title": titles.get(key) or "",
            "cwd": cwd,
            "first_ts": first,
            "est_calls": est,
            "actual_calls": actual,
            "ratio": actual / est if est else None,
            "miss": _miss(est, actual),
            "usd": usd,
        }
        for key, est, actual, usd, first, cwd in conn.execute(
            _SESSIONS, filters.params()
        )
    ]
    return sorted(rows, key=lambda r: (-_spread(r), r["session_id"]))


def _events(
    conn: sqlite3.Connection, filters: Filters
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Gate misses per day and kind (newest first), and per day (in order)."""
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    daily: defaultdict[str, int] = defaultdict(int)
    for ts, kind, detail in conn.execute(
        _EVENTS, (SOURCE, filters.since, filters.until)
    ):
        day = _db.day_of(ts)
        row = groups.setdefault(
            (day, kind), {"day": day, "kind": kind, "count": 0, "example": ""}
        )
        row["count"] += 1
        row["example"] = detail
        daily[day] += 1
    rows = sorted(groups.values(), key=lambda r: (r["day"], r["count"]), reverse=True)
    return rows, [{"day": d, "count": n} for d, n in sorted(daily.items())]


def _share(rows: list[dict[str, Any]], miss: str) -> float | None:
    """Share of sessions with this miss flag."""
    return _db.ratio(sum(r["miss"] == miss for r in rows), len(rows))


@panel(
    "estimator",
    "Task-size estimator",
    order=84,
    tables={"sessions": {"limit": str(TOP)}, "events": {"limit": str(TOP)}},
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Estimated vs actual calls per session, and gate misses per kind/day."""
    sessions = _sessions(conn, filters)
    events, daily = _events(conn, filters)
    ratios = [r["ratio"] for r in sessions if r["ratio"] is not None]
    return {
        "caption": CAPTION,
        "filtered_by": FILTERED_BY,
        "totals": {
            "sessions": len(sessions),
            "within_share": _share(sessions, ""),
            "over_share": _share(sessions, "over"),
            "under_share": _share(sessions, "under"),
            "median_ratio": median(ratios) if ratios else None,
            "gate_misses": sum(d["count"] for d in daily),
            "predicted_fits": sum(
                r["count"] for r in events if r["kind"] == "predicted-fits"
            ),
        },
        "sessions": sessions,
        "events": events,
        "events_daily": daily,
    }
