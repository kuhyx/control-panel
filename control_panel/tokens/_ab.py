"""A/B panel: judgment subagents on Sonnet vs Opus, precomputed by the ingester.

The verdict (``banner``) is decided in testsAndMisc's ``token_dashboard.ab``
with Wilson intervals; this module only serves it -- as a panel, on every
/tokens view (via the index), and bare at ``/api/tokens/ab`` for the tray.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from control_panel.tokens import _db
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

COLLECTING = {"level": "grey", "text": "A/B judgment agents: collecting (n=0)"}


def payload(conn: sqlite3.Connection) -> dict[str, Any]:
    """The stored A/B summary, or an empty collecting one."""
    raw = _db.meta_json(conn, "ab")
    return raw if isinstance(raw, dict) else {"arms": {}, "banner": COLLECTING}


def banner(conn: sqlite3.Connection) -> dict[str, Any]:
    """Just the RED / GREEN / GREY verdict."""
    found = payload(conn).get("banner")
    return found if isinstance(found, dict) else COLLECTING


@panel("ab", "A/B: judgment subagents", order=35)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Per-arm rates with Wilson CIs and per-arm differences (all time)."""
    del filters  # an A/B verdict over a sub-range would only lose power
    return payload(conn)
