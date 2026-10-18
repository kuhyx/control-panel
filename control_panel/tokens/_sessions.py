"""Sessions panel (ranked list) and the per-session drill-down.

A session's headline time is **active** time: the union of its main and
subagent records' activity, gaps over five minutes counted as zero. Wall time
(first to last record) is shown beside it.
"""

from __future__ import annotations

from collections import defaultdict
import json
from typing import TYPE_CHECKING, Any

from control_panel.tokens import _db
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

LIMIT = 200
_COLUMNS = (
    "key",
    "cwd",
    "title",
    "first_ts",
    "last_ts",
    "wall_s",
    "active_s",
    "usd",
    "usd_main",
    "usd_sub",
    "calls",
    "prompts",
    "subagents",
    "models",
    "final_tag",
)
# Literal column list matching _COLUMNS (kept literal: no SQL built from strings).
_LIST = (
    "SELECT key, cwd, title, first_ts, last_ts, wall_s, active_s, usd, usd_main,"
    " usd_sub, calls, prompts, subagents, models, final_tag FROM session_summary"
    " WHERE first_ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR models LIKE '%\"' || ? || '\"%')"
    " ORDER BY usd DESC LIMIT ?"
)
_ONE = (
    "SELECT key, cwd, title, first_ts, last_ts, wall_s, active_s, usd, usd_main,"
    " usd_sub, calls, prompts, subagents, models, final_tag FROM session_summary"
    " WHERE key = ?"
)


def _session(row: tuple[Any, ...]) -> dict[str, Any]:
    """A summary row as a dict, models decoded."""
    out = dict(zip(_COLUMNS, row, strict=True))
    out["models"] = json.loads(out["models"] or "{}")
    return out


@panel("sessions", "Sessions", order=20)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """The costliest sessions that started inside the filters."""
    rows = conn.execute(
        _LIST,
        (
            filters.since,
            filters.until,
            filters.cwd,
            filters.cwd,
            filters.cwd,
            filters.model,
            filters.model,
            LIMIT,
        ),
    ).fetchall()
    return {"sessions": [_session(r) for r in rows], "limit": LIMIT}


def _subagents(conn: sqlite3.Connection, key: str) -> dict[int | None, list[Any]]:
    """Subagents of a session grouped by spawning prompt (None: unattributed)."""
    grouped: dict[int | None, list[Any]] = defaultdict(list)
    for row in conn.execute(
        "SELECT sub_key, prompt_idx, depth, description, agent_type, model,"
        " usd, calls, wall_s, active_s FROM subagent_link WHERE main_key = ?"
        " ORDER BY usd DESC",
        (key,),
    ):
        grouped[row[1]].append(
            {
                "key": row[0],
                "depth": row[2],
                "description": row[3],
                "agent_type": row[4],
                "model": row[5],
                "usd": row[6],
                "calls": row[7],
                "wall_s": row[8],
                "active_s": row[9],
            }
        )
    return grouped


def _tools(conn: sqlite3.Connection, key: str) -> dict[int, list[Any]]:
    """Non-subagent tool calls per prompt, grouped by tool name."""
    grouped: dict[int, list[Any]] = defaultdict(list)
    for idx, name, calls, tokens, usd, carry in conn.execute(
        "SELECT prompt_idx, name, SUM(calls), SUM(result_tokens), SUM(usd),"
        " SUM(carry_usd) FROM tool_use WHERE key = ? GROUP BY prompt_idx, name"
        " ORDER BY SUM(usd) DESC",
        (key,),
    ):
        grouped[idx].append(
            {
                "name": name,
                "calls": calls,
                "result_tokens": tokens,
                "usd": usd,
                "carry_usd": carry,
            }
        )
    return grouped


def detail(conn: sqlite3.Connection, key: str) -> dict[str, Any] | None:
    """One session: summary, prompts by cost with subagents and tools."""
    row = conn.execute(_ONE, (key,)).fetchone()
    if row is None:
        return None
    subagents = _subagents(conn, key)
    tools = _tools(conn, key)
    prompts = []
    for idx, ts, text, own, sub, active_s, wall_s, calls in conn.execute(
        "SELECT idx, ts, text, usd_own, usd_sub, active_s, wall_s, calls"
        " FROM prompt_summary WHERE key = ?",
        (key,),
    ):
        usd = own + sub
        prompts.append(
            {
                "idx": idx,
                "ts": ts,
                "text": text,
                "usd": usd,
                "usd_own": own,
                "usd_sub": sub,
                "active_s": active_s,
                "wall_s": wall_s,
                "calls": calls,
                "subagents": subagents.get(idx, []),
                "tools": [
                    t | {"share": _db.ratio(t["usd"], own)} for t in tools.get(idx, [])
                ],
            }
        )
    prompts.sort(key=lambda p: -p["usd"])
    return {
        "session": _session(row),
        "prompts": prompts,
        "unattributed": subagents.get(None, []),
    }
