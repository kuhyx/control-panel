"""A/B panel: judgment subagents on Sonnet vs Opus, precomputed by the ingester.

The verdict (``banner``) is decided in testsAndMisc's ``token_dashboard.ab``
with Wilson intervals; this module only serves it -- as a panel, on every
/tokens view (via the index), and bare at ``/api/tokens/ab`` for the tray.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from control_panel.tokens import _ab_rows, _ab_stats, _db
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

COLLECTING = {"level": "grey", "text": "A/B judgment agents: collecting (n=0)"}
BUILD_COLLECTING = {"level": "grey", "text": "A/B build agents: collecting (n=0)"}


def payload(conn: sqlite3.Connection) -> dict[str, Any]:
    """The stored A/B summary, or an empty collecting one."""
    raw = _db.meta_json(conn, "ab")
    return raw if isinstance(raw, dict) else {"arms": {}, "banner": COLLECTING}


def build_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    """The build-class A/B (agent-ab-build.jsonl), all time, with its rows."""
    raw = _db.meta_json(conn, "ab_build")
    found = raw if isinstance(raw, dict) else {"arms": {}, "banner": BUILD_COLLECTING}
    return {**found, "metrics": _ab_rows.rows(found)}


def banner(conn: sqlite3.Connection) -> dict[str, Any]:
    """Just the RED / GREEN / GREY verdict."""
    found = payload(conn).get("banner")
    return found if isinstance(found, dict) else COLLECTING


_ROWS = (
    "SELECT arm, usd, duration_s, redo, followup, error, correction, tag"
    " FROM ab_rows WHERE"
    " (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
)
_COLUMNS = (
    "arm",
    "usd",
    "duration_s",
    "redo",
    "followup",
    "error",
    "correction",
    "tag",
)


def _has_rows(conn: sqlite3.Connection) -> bool:
    """Whether the ingester stored per-assignment rows (newer stores only)."""
    found = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ab_rows'"
    ).fetchone()
    return found is not None


@panel("ab", "A/B: judgment subagents", order=35)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Per-arm rates with Wilson CIs and per-arm differences, all time.

    The date range is ignored on purpose (a verdict over a sub-range only
    loses power); cwd, model and scope recount the arms from ``ab_rows``.
    The banner stays the all-time verdict either way.
    """
    stored = payload(conn)
    scoped = (filters.cwd, filters.model) != ("", "") or filters.scope != "all"
    if not scoped or not _has_rows(conn):
        return {
            **stored,
            "metrics": _ab_rows.rows(stored),
            "filtered_by": "all time, all assignments",
            "build": build_payload(conn),
        }
    rows = [
        dict(zip(_COLUMNS, row, strict=True))
        for row in conn.execute(_ROWS, filters.params()[2:])
    ]
    recount = {**stored, **_ab_stats.summary(rows)}
    return {
        **recount,
        "metrics": _ab_rows.rows(recount),
        "filtered_by": "all time; arms recounted for cwd/model/scope",
        "build": build_payload(conn),
    }
