"""Row builders for the detail tables (calls, marks, turn_detail).

Each panel group's test inserts the rows it needs into the store that
:func:`_fixture_tokens.build` made; defaults match that store's session
``s1`` (main, cwd ``/home/tester/src/a``, Opus, day 2026-09-28).
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


def _ts(kw: dict[str, object]) -> float:
    """The row's timestamp (default: the fixture's first instant)."""
    value = kw.get("ts", T0)
    return float(value) if isinstance(value, int | float) else T0


def _owner(kw: dict[str, object]) -> tuple[object, ...]:
    """key, main_key, is_sub, cwd, model, ts, day, prompt_idx."""
    key = str(kw.get("key", "s1"))
    return (
        key,
        kw.get("main", key.split("/", maxsplit=1)[0]),
        int("/" in key),
        kw.get("cwd", CWD),
        kw.get("model", OPUS),
        _ts(kw),
        kw.get("day", "2026-09-28"),
        kw.get("prompt", 0),
    )


def call(**kw: object) -> tuple[object, ...]:
    """One ``calls`` row; any column may be overridden by name."""
    return (
        *_owner(kw),
        kw.get("end_ts", _ts(kw) + 2),
        kw.get("name", "Bash"),
        kw.get("family", "git status"),
        kw.get("target", "git status"),
        kw.get("sig", "sig-1"),
        kw.get("batch", 1),
        kw.get("result_tokens", 100),
        kw.get("images", 0),
        kw.get("is_error", 0),
        kw.get("error_kind", ""),
        kw.get("create_usd", 0.01),
        kw.get("carry_usd", 0.1),
        kw.get("carry_calls", 5),
    )


def mark(**kw: object) -> tuple[object, ...]:
    """One ``marks`` row."""
    return (
        *_owner(kw),
        kw.get("kind", "hook_run"),
        kw.get("name", "PreToolUse:Bash"),
        kw.get("detail", "time_cap.sh"),
        kw.get("count", 1),
        kw.get("tokens", 0),
        kw.get("extra", 0),
        kw.get("duration_ms", 10),
        kw.get("retry_usd", 0.0),
        kw.get("create_usd", 0.0),
        kw.get("carry_usd", 0.0),
        kw.get("carry_calls", 0),
    )


def turn_detail(**kw: object) -> tuple[object, ...]:
    """One ``turn_detail`` row."""
    return (
        *_owner(kw),
        kw.get("latency_s", 5.0),
        kw.get("cw_1h", 1000),
        kw.get("cw_5m", 0),
        kw.get("out_text", 100),
        kw.get("out_tool", 50),
        kw.get("out_think", 300),
        kw.get("tool_calls", 1),
    )


def insert(
    path: Path,
    calls: Sequence[tuple[object, ...]] = (),
    marks: Sequence[tuple[object, ...]] = (),
    turns: Sequence[tuple[object, ...]] = (),
) -> None:
    """Add detail rows to an existing fixture store."""
    with closing(sqlite3.connect(path)) as conn:
        conn.executemany(
            "INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            calls,
        )
        conn.executemany(
            "INSERT INTO marks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            marks,
        )
        conn.executemany(
            "INSERT INTO turn_detail VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", turns
        )
        conn.commit()
