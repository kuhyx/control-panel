"""Rows for the standing-prefix panel's tests: size history and snapshots.

The base store (:func:`_fixture_tokens.build`) lists four context files --
global CLAUDE.md and MEMORY.md always loaded, a repo CLAUDE.md, and a gone
``rules`` file -- and one git size point for CLAUDE.md at ``T0 - DAY``.
"""

from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def context_files(path: Path) -> dict[str, str]:
    """The fixture's context-file paths by kind."""
    with closing(sqlite3.connect(path)) as conn:
        return dict(conn.execute("SELECT kind, path FROM context_files"))


def sizes(path: Path, rows: Sequence[tuple[str, float, int, str]]) -> None:
    """Add ``context_sizes`` rows: (path, ts, bytes, source)."""
    with closing(sqlite3.connect(path)) as conn:
        conn.executemany("INSERT INTO context_sizes VALUES (?,?,?,?)", rows)
        conn.commit()


def snapshot(path: Path, name: str, until: float, standing: int) -> None:
    """Add a token_audit snapshot carrying ``standing_tokens_est``."""
    metrics = json.dumps({"usd_per_day": 1.0, "standing_tokens_est": standing})
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(
            "INSERT INTO snapshots VALUES (?,?,?,?,?)",
            (name, name, until - 86400, until, metrics),
        )
        conn.commit()
