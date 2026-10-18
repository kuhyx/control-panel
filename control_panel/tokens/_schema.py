"""``GET /api/tokens/schema``: an OpenAPI-ish description of this API.

Endpoints, the shared filters, the table grammar (see :mod:`_tables`) and,
per panel, every table it returns with each column's kind -- read from a
live build of the panel under the default filters, so it cannot drift from
what the panel really sends.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from control_panel.tokens import _db, _tables
from control_panel.tokens._registry import PANELS

if TYPE_CHECKING:
    import sqlite3

FILTERS = {
    "from": "first local day, YYYY-MM-DD (default: 30 days before `to`)",
    "to": "last local day, YYYY-MM-DD (default: now)",
    "window": "a token_audit snapshot name: use its exact window instead",
    "cwd": "repo/cwd prefix: that directory and everything under it",
    "model": "exact model id",
    "scope": "all | main | sub (main sessions or subagents only)",
}
TABLE_PARAMS = {
    "t.<table>.q": "case-insensitive text search over every scalar column",
    "t.<table>.f.<column>": (
        "column filter: ~text (contains) | lo..hi (numeric, either end"
        " optional) | =a|b (one of)"
    ),
    "t.<table>.sort": "comma-separated columns, '-' prefix = descending; nulls last",
    "t.<table>.limit": "at most n rows; 0 = all",
}
ENDPOINTS = {
    "GET /api/tokens": "panel list, filter options, data coverage, A/B banner",
    "GET /api/tokens/panel/<name>": "one panel under the filters and table params",
    "GET /api/tokens/session/<key>": (
        "one session: prompts, prompts.tools, prompts.subagents, unattributed"
    ),
    "GET /api/tokens/context-file?path=<path>": "one listed context file",
    "GET /api/tokens/ab": "A/B judgment-agent payload (the tray reads this)",
    "GET /api/tokens/schema": "this document",
}


def _panel_tables(conn: sqlite3.Connection, now: float) -> dict[str, Any]:
    """Each panel's tables and column kinds, from a default build."""
    filters = _db.parse_filters(conn, "", now)
    out: dict[str, Any] = {}
    for name, found in sorted(PANELS.items()):
        meta = _tables.apply(found.build(conn, filters), "", found.tables)["_tables"]
        out[name] = {
            "title": found.title,
            "default_table_params": found.tables or {},
            "tables": {
                table: {col: info["kind"] for col, info in entry["columns"].items()}
                for table, entry in meta.items()
            },
        }
    return out


def document(conn: sqlite3.Connection, now: float) -> dict[str, Any]:
    """The whole description."""
    return {
        "name": "control-panel /api/tokens",
        "read_only": True,
        "units": {
            "usd": "API list-price dollars (not the subscription bill)",
            "tokens": "estimated where not billed: 4 chars/token, ~2.6k per image",
            "*_s": "seconds",
            "*_share": "fraction 0..1",
            "ts": "unix seconds",
        },
        "endpoints": ENDPOINTS,
        "filters": FILTERS,
        "table_params": TABLE_PARAMS,
        "response_extras": {
            "_tables": "per table: total, matched, shown, columns{kind, values}"
        },
        "panels": _panel_tables(conn, now),
    }
