"""Extra store rows for the subagent / session / spend panel tests.

:func:`_fixture_tokens.build` writes turns with zero token counts and one
subagent; these builders add turns that carry tokens, more subagents, the
Agent calls that spawned them, prompts and events.
"""

from __future__ import annotations

from contextlib import closing
import sqlite3
from typing import TYPE_CHECKING

from control_panel.tests._fixture_tokens import T0

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

CWD = "/home/tester/src/a"
OPUS = "claude-opus-5-5"


def turn(
    key: str, ts: float = T0, usd: float = 1.0, **kw: object
) -> tuple[object, ...]:
    """One ``turns`` row; ``tokens`` = (input, cache_write, cache_read, output)."""
    tokens = kw.get("tokens", (0, 0, 0, 0))
    assert isinstance(tokens, tuple)
    return (
        key,
        kw.get("main", key.split("/", maxsplit=1)[0]),
        int("/" in key),
        kw.get("cwd", CWD),
        ts,
        kw.get("day", "2026-09-28"),
        kw.get("model", OPUS),
        usd,
        kw.get("context", 1000),
        kw.get("prompt", 0),
        *tokens,
    )


def link(sub_key: str, **kw: object) -> tuple[object, ...]:
    """One ``subagent_link`` row."""
    return (
        sub_key,
        sub_key.split("/", maxsplit=1)[0],
        kw.get("prompt", 0),
        1,
        kw.get("description", "Do x"),
        kw.get("agent_type", "general-purpose"),
        kw.get("model", OPUS),
        kw.get("usd", 1.0),
        kw.get("calls", 1),
        kw.get("first_ts", T0),
        kw.get("last_ts", T0 + 60),
        kw.get("wall_s", 60.0),
        kw.get("active_s", 30.0),
    )


def agent_call(key: str, agent_id: str, ts: float, **kw: object) -> tuple[object, ...]:
    """One ``agent_calls`` row (the parent's spawn of ``agent-<agent_id>``)."""
    return (
        key,
        f"toolu_{agent_id}",
        agent_id,
        kw.get("prompt", 0),
        ts,
        kw.get("description", "Do x"),
        kw.get("agent_type", "general-purpose"),
        kw.get("model", ""),
        ts + 60,
        "completed",
    )


def insert(
    path: Path,
    *,
    turns: Sequence[tuple[object, ...]] = (),
    links: Sequence[tuple[object, ...]] = (),
    agent_calls: Sequence[tuple[object, ...]] = (),
    prompts: Sequence[tuple[object, ...]] = (),
) -> None:
    """Add rows to an existing fixture store."""
    with closing(sqlite3.connect(path)) as conn:
        conn.executemany(
            "INSERT INTO turns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", turns
        )
        conn.executemany(
            "INSERT INTO subagent_link VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", links
        )
        conn.executemany(
            "INSERT INTO agent_calls VALUES (?,?,?,?,?,?,?,?,?,?)", agent_calls
        )
        conn.executemany("INSERT INTO prompts VALUES (?,?,?,?,?)", prompts)
        conn.commit()
