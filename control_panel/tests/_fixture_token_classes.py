"""Turns rows with token classes (the base fixture's turns carry none).

Shared by the token-classes, context-growth, output and latency tests:
:func:`turn` builds one ``turns`` row, :func:`add` writes turns and prompts
into a store made by :func:`_fixture_tokens.build`.
"""

from __future__ import annotations

from contextlib import closing
import sqlite3
from typing import TYPE_CHECKING

from control_panel.tests._fixture_detail import CWD, OPUS
from control_panel.tests._fixture_tokens import T0

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def turn(**kw: object) -> tuple[object, ...]:
    """One ``turns`` row; defaults: session ``s3``, main, Opus, 2026-09-28."""
    key = str(kw.get("key", "s3"))
    return (
        key,
        kw.get("main", key.split("/", maxsplit=1)[0]),
        int("/" in key),
        kw.get("cwd", CWD),
        kw.get("ts", T0),
        kw.get("day", "2026-09-28"),
        kw.get("model", OPUS),
        kw.get("usd", 0.0),
        kw.get("context", 1000),
        kw.get("prompt", 0),
        kw.get("input", 0),
        kw.get("cache_write", 0),
        kw.get("cache_read", 0),
        kw.get("output", 0),
    )


def add(
    path: Path,
    turns: Sequence[tuple[object, ...]] = (),
    prompts: Sequence[tuple[object, ...]] = (),
) -> None:
    """Append ``turns`` rows and ``prompts`` rows (key, idx, ts, id, text)."""
    with closing(sqlite3.connect(path)) as conn:
        conn.executemany(
            "INSERT INTO turns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", turns
        )
        conn.executemany("INSERT INTO prompts VALUES (?,?,?,?,?)", prompts)
        conn.commit()
