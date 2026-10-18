"""Efficiency panel: three weekly 0-token ratios, precomputed by the ingester.

Each carries a caption naming exactly what it measures and its weakness; the
frontend shows the caption under the chart, so the number is never read
without its caveat.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from control_panel.tokens import _db
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
}


@panel("efficiency", "Efficiency", order=30)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """The three weekly series inside the date range, with captions."""
    raw = _db.meta_json(conn, "efficiency")
    data = raw if isinstance(raw, dict) else {}
    low = _db.monday(_db.day_of(filters.since))
    high = _db.day_of(filters.until)
    return {
        "captions": CAPTIONS,
        "filtered_by": "date range only (precomputed weekly)",
        **{
            name: [w for w in data.get(name, []) if low <= w["week"] <= high]
            for name in CAPTIONS
        },
    }
