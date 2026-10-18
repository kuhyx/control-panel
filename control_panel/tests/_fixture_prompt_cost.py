"""Rows for the cost-per-prompt panel's tests.

The base store (:func:`_fixture_tokens.build`) already has two prompts of
session ``s1`` (``fix a``: $2 own + $3 subagents; ``and b``: $1 own).
"""

from __future__ import annotations

from contextlib import closing
import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def prompts(
    path: Path, rows: Sequence[tuple[str, int, float, str, float, float]]
) -> None:
    """Add ``prompt_summary`` rows: (key, idx, ts, text, usd_own, usd_sub)."""
    with closing(sqlite3.connect(path)) as conn:
        conn.executemany(
            "INSERT INTO prompt_summary VALUES (?,?,?,?,?,?,60,60,2)", rows
        )
        conn.commit()
