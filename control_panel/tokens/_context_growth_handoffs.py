"""Handoff documents in the transcripts, for the context-size panel.

A handoff is spotted three ways: a ``Write`` call whose target path contains
"handoff" (any case: the doc was generated), a user prompt mentioning it
(usually "Read <handoff> and continue": the doc was picked up), or a hook
mark whose detail names one. Handoffs written by a script outside a tool
call are invisible here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TEXT = 200  # characters of a prompt shown

_WRITES = (
    "SELECT ts, key, target FROM calls WHERE name = 'Write'"
    " AND target LIKE '%handoff%' AND"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
)
_MARKS = (
    "SELECT ts, key, kind || ': ' || detail FROM marks"
    " WHERE detail LIKE '%handoff%' AND"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
)
# The prompts table has no filter columns: a prompt counts when the filtered
# turns include a call of the same key and prompt index.
_PROMPT_KEYS = (
    "SELECT DISTINCT key, prompt_idx FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
)
_PROMPTS = "SELECT key, idx, ts, text FROM prompts WHERE text LIKE '%handoff%'"


def handoffs(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Every handoff sighting, newest first."""
    rows = [
        {"ts": ts, "key": key, "source": "write", "detail": target}
        for ts, key, target in conn.execute(_WRITES, filters.params())
    ]
    rows += [
        {"ts": ts, "key": key, "source": "mark", "detail": detail}
        for ts, key, detail in conn.execute(_MARKS, filters.params())
    ]
    seen = set(conn.execute(_PROMPT_KEYS, filters.params()).fetchall())
    rows += [
        {"ts": ts, "key": key, "source": "prompt", "detail": text[:TEXT]}
        for key, idx, ts, text in conn.execute(_PROMPTS)
        if (key, idx) in seen
    ]
    return sorted(rows, key=lambda r: -r["ts"])
