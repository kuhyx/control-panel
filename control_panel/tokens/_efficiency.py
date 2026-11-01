"""Efficiency panel: three weekly 0-token ratios, computed live under the filters.

Each carries a caption naming exactly what it measures and its weakness; the
frontend shows the caption under the chart, so the number is never read
without its caveat.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from control_panel.tokens import _efficiency_notes, _efficiency_weeks
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

CAPTIONS = {
    "done": (
        "USD per DONE session: a week's spend on status-tagged sessions / those "
        "ending on DONE:. Weakness: DONE is self-reported, and one session can "
        "finish several tasks or half of one; untagged sessions are left out."
    ),
    "commits": (
        "USD per surviving commit: a week's spend / its Claude commits still "
        "standing 14 days later (not reverted, >=50% of added lines still blamed "
        "to them). Weakness: commit size varies wildly and younger commits are "
        "pending."
    ),
    "estimate": (
        "USD per estimated size unit: spend of sessions the task-size estimator "
        "sized / its pre-work est_calls. Noisy (estimator precision ~0.7)."
    ),
    "notes": _efficiency_notes.CAPTION,
}


@panel("efficiency", "Efficiency", order=30)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """The weekly series under every filter, plus per-note cost, with captions."""
    rows = _efficiency_weeks.sessions(conn, filters)
    notes = _efficiency_notes.read()
    return {
        "captions": CAPTIONS,
        "filtered_by": (
            "date range, cwd, model, scope (a session's spend = its matching turns)"
        ),
        "done": _efficiency_weeks.done(rows),
        "commits": _efficiency_weeks.commits(conn, rows, filters.until),
        "estimate": _efficiency_weeks.estimate(conn, rows),
        "notes": notes,
        "notes_weekly": _efficiency_notes.weekly(notes, filters.since, filters.until),
    }
