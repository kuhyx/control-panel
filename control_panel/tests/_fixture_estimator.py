"""Rows for the task-size estimator panel's tests: estimates and miss events.

The base store (:func:`_fixture_tokens.build`) has session ``s1`` (2 main
calls + 1 subagent call) and ``s2`` (1 call, cwd ``/home/tester``).
"""

from __future__ import annotations

from contextlib import closing
import sqlite3
from typing import TYPE_CHECKING

from control_panel.tests._fixture_tokens import T0

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def estimates(path: Path, rows: Sequence[tuple[str, int]]) -> None:
    """Add ``estimates`` rows: (session_id, est_calls)."""
    with closing(sqlite3.connect(path)) as conn:
        conn.executemany("INSERT INTO estimates VALUES (?,?)", rows)
        conn.commit()


def turn(path: Path, key: str, ts: float = T0) -> None:
    """Add one main-session API call (cwd ``/home/tester/src/a``, Opus)."""
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(
            "INSERT INTO turns VALUES (?,?,0,'/home/tester/src/a',?,"
            "'2026-09-28','claude-opus-5-5',0.5,1000,0,0,0,0,0)",
            (key, key, ts),
        )
        conn.commit()


def events(path: Path, rows: Sequence[tuple[str, float, str, str]]) -> None:
    """Add ``events`` rows: (source, ts, kind, detail)."""
    with closing(sqlite3.connect(path)) as conn:
        conn.executemany("INSERT INTO events VALUES (?,?,?,?)", rows)
        conn.commit()
