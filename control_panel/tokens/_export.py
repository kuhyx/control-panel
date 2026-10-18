"""Raw rows for export: every API call, tool call and context mark.

The other panels aggregate; this one hands out the rows underneath them,
under the same filters and table parameters, so any view can be rebuilt
elsewhere (CSV / JSON / Copy for Claude from the table, or the API with
``t.<table>.limit=0`` for every row).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

SHOWN = "100"  # rows per table by default
MAX_ROWS = 200_000

_TURNS = (
    "SELECT t.ts, t.key, t.cwd, t.model, t.usd, t.context, t.input,"
    " t.cache_write, t.cache_read, t.output, d.latency_s, d.out_think FROM turns t"
    " LEFT JOIN turn_detail d ON d.key = t.key AND d.ts = t.ts WHERE"
    " t.ts BETWEEN ? AND ?"
    " AND (? = '' OR t.cwd = ? OR t.cwd LIKE ? || '/%')"
    " AND (? = '' OR t.model = ?)"
    " AND (? = -1 OR t.is_sub = ?)"
    " ORDER BY t.ts DESC LIMIT ?"
)
_CALLS = (
    "SELECT ts, key, cwd, model, name, family, target, result_tokens,"
    " error_kind, create_usd, carry_usd, carry_calls FROM calls WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " ORDER BY ts DESC LIMIT ?"
)
_MARKS = (
    "SELECT ts, key, cwd, model, kind, name, detail, count, tokens,"
    " duration_ms, retry_usd, create_usd, carry_usd FROM marks WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " ORDER BY ts DESC LIMIT ?"
)
COLUMNS = {
    "turns": (
        "ts",
        "key",
        "cwd",
        "model",
        "usd",
        "context",
        "input",
        "cache_write",
        "cache_read",
        "output",
        "latency_s",
        "out_think",
    ),
    "calls": (
        "ts",
        "key",
        "cwd",
        "model",
        "name",
        "family",
        "target",
        "result_tokens",
        "error_kind",
        "create_usd",
        "carry_usd",
        "carry_calls",
    ),
    "marks": (
        "ts",
        "key",
        "cwd",
        "model",
        "kind",
        "name",
        "detail",
        "count",
        "tokens",
        "duration_ms",
        "retry_usd",
        "create_usd",
        "carry_usd",
    ),
}
QUERIES = {"turns": _TURNS, "calls": _CALLS, "marks": _MARKS}


@panel(
    "export",
    "Raw rows (export)",
    order=99,
    tables={t: {"limit": SHOWN} for t in COLUMNS},
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Newest rows first; every filter and table parameter applies."""
    return {
        "caption": (
            "Raw rows under the filters, newest first: API calls (turns), tool "
            "calls (calls, with creation/carry cost) and context marks (hooks, "
            "attachments, compactions, API errors). Use Show all, then CSV / "
            "Copy as JSON, or the API with t.<table>.limit=0."
        ),
        **{
            name: [
                dict(zip(columns, row, strict=True))
                for row in conn.execute(QUERIES[name], (*filters.params(), MAX_ROWS))
            ]
            for name, columns in COLUMNS.items()
        },
    }
