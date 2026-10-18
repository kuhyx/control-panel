"""The three weekly efficiency series, computed live under the filters.

The same rules as testsAndMisc's ``token_dashboard.efficiency`` (which
precomputes the unfiltered series), but a session's spend is the sum of its
turns that match the page's filters, so cwd, model and scope apply.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens import _db

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

SURVIVAL_WINDOW_S = 14 * 86400  # token_dashboard.survival.WINDOW_DAYS
LOST = frozenset({"churned", "reverted"})  # survival.FINAL minus "survived"
Week = dict[str, Any]

_SPEND = (
    "SELECT main_key, SUM(usd) FROM turns WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " GROUP BY main_key"
)


def _week(stamp: float) -> str:
    """Monday (local) of the week containing ``stamp``."""
    return _db.monday(_db.day_of(stamp))


def sessions(
    conn: sqlite3.Connection, filters: Filters
) -> list[tuple[str, float, float, Any]]:
    """``(key, first_ts, filtered usd, end tag)`` of every session with spend."""
    spend = dict(conn.execute(_SPEND, filters.params()).fetchall())
    rows = conn.execute("SELECT key, first_ts, final_tag FROM session_summary")
    return [(key, first, spend[key], tag) for key, first, tag in rows if key in spend]


def done(rows: list[tuple[str, float, float, Any]]) -> list[Week]:
    """USD per DONE session and the DONE share, per week."""
    weeks: dict[str, Week] = defaultdict(
        lambda: {"done": 0, "other": 0, "untagged": 0, "usd_tagged": 0.0}
    )
    for _key, first, usd, tag in rows:
        week = weeks[_week(first)]
        if tag is None:
            week["untagged"] += 1
            continue
        week["usd_tagged"] += usd
        week["done" if tag == "DONE" else "other"] += 1
    return [
        weeks[name]
        | {
            "week": name,
            "usd_per_done": _db.ratio(weeks[name]["usd_tagged"], weeks[name]["done"]),
            "done_share": _db.ratio(
                weeks[name]["done"], weeks[name]["done"] + weeks[name]["other"]
            ),
        }
        for name in sorted(weeks)
    ]


def commits(
    conn: sqlite3.Connection, rows: list[tuple[str, float, float, Any]], now: float
) -> list[Week]:
    """USD per surviving commit of the filtered sessions, per week."""
    keys = {key for key, *_ in rows}
    week_usd: dict[str, float] = defaultdict(float)
    for _key, first, usd, _tag in rows:
        week_usd[_week(first)] += usd
    weeks: dict[str, Week] = defaultdict(
        lambda: {"survived": 0, "lost": 0, "pending": 0, "unknown": 0}
    )
    for key, ts, verdict in conn.execute(
        "SELECT c.key, c.ts, v.verdict FROM session_commits c"
        " LEFT JOIN commit_verdicts v ON v.sha = c.sha"
    ):
        if key.split("/", 1)[0] not in keys:
            continue
        week = weeks[_week(ts)]
        if verdict == "survived":
            week["survived"] += 1
        elif verdict in LOST:
            week["lost"] += 1
        elif verdict == "pending" or (verdict is None and now - ts < SURVIVAL_WINDOW_S):
            week["pending"] += 1
        else:
            week["unknown"] += 1
    return [
        weeks[name]
        | {
            "week": name,
            "usd": week_usd.get(name, 0.0),
            "usd_per_survivor": _db.ratio(
                week_usd.get(name, 0.0), weeks[name]["survived"]
            ),
        }
        for name in sorted(weeks)
    ]


def estimate(
    conn: sqlite3.Connection, rows: list[tuple[str, float, float, Any]]
) -> list[Week]:
    """USD per estimated call, over sessions the estimator sized."""
    est = dict(conn.execute("SELECT session_id, est_calls FROM estimates").fetchall())
    weeks: dict[str, Week] = defaultdict(lambda: {"usd": 0.0, "est_calls": 0, "n": 0})
    for key, first, usd, _tag in rows:
        if key not in est:
            continue
        week = weeks[_week(first)]
        week["usd"] += usd
        week["est_calls"] += est[key]
        week["n"] += 1
    return [
        weeks[name]
        | {
            "week": name,
            "usd_per_unit": _db.ratio(weeks[name]["usd"], weeks[name]["est_calls"]),
        }
        for name in sorted(weeks)
    ]
