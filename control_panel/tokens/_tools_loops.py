"""The runaway-loop rule shared by the Tools and Anomalies panels.

A *loop* is the same tool call -- same transcript key and the same ``sig``
(the ingester's hash of name + input, so identical calls share it) -- made
more than :data:`REPEATS` times. Its cost is what those copies' results cost
in context (creation + carry, see ``_carry``), not the calls' own output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

REPEATS = 2  # more than this many identical calls is a loop
CAPTION = (
    "Loops: the same transcript repeating an identical tool call (same name and "
    "input, so the same sig) more than twice; cost = the copies' context "
    "creation + carry. A deliberate re-run (a test after each fix) counts too."
)

_LOOPS = (
    "SELECT key, MIN(name), MIN(target), COUNT(*), SUM(create_usd + carry_usd)"
    " FROM calls WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY key, sig HAVING COUNT(*) > ?"
)


def loops(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Every loop in the filters, the costliest first."""
    rows = [
        {
            "key": key,
            "name": name,
            "target": target,
            "repeats": repeats,
            "cost_usd": cost or 0.0,
        }
        for key, name, target, repeats, cost in conn.execute(
            _LOOPS, (*filters.params(), REPEATS)
        )
    ]
    return sorted(rows, key=lambda r: (-r["cost_usd"], -r["repeats"]))
