"""Context files inspector: every file that enters Claude's context.

The list (and each file's size history) comes from the store; size, tokens
and content are read live from disk on every request, so a file edited a
minute ago shows its new size. A file's standing cost is
``tokens x calls/day x cache-read price``: every API call re-reads the whole
prefix from cache. Repo CLAUDE.md files only count calls made inside the repo;
skills and agents only count their description (what is always loaded).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING, Any

from control_panel import _sysroot
from control_panel.tokens import _db
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

BYTES_PER_TOKEN = 4  # token_audit.surfaces.BYTES_PER_TOKEN
WINDOW_DAYS = 7
WARN_SHARE = 0.85
LOG_LINES = 30
GIT = "/usr/bin/git"  # absolute: never resolved through a caller-controlled PATH


def _read(path: str) -> str | None:
    """A file's text, or ``None`` when it is gone or unreadable."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _standing_bytes(text: str, standing: str) -> int:
    """Bytes always in context: the description for skills and agents."""
    if standing != "description":
        return len(text.encode())
    _, _, rest = text[:4000].partition("description:")
    return len(rest.split("\n---", 1)[0].encode()) if rest else 0


def _calls_per_day(conn: sqlite3.Connection, now: float, cwd: str = "") -> float:
    """API calls per day over the last week, optionally inside one repo."""
    count = conn.execute(
        "SELECT COUNT(*) FROM turns WHERE ts > ?"
        " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')",
        (now - WINDOW_DAYS * 86400, cwd, cwd, cwd),
    ).fetchone()[0]
    return float(count) / WINDOW_DAYS


def _repo_cwd(path: str) -> str:
    """The cwd a repo CLAUDE.md applies to (test roots stripped)."""
    repo = str(Path(path).parent)
    root = _sysroot.sysroot()
    return repo[len(root) :] if root and repo.startswith(root) else repo


def _warning(size: int, limit: int | None) -> str | None:
    """Say so when a file is near or over its limit."""
    if limit is None or size < WARN_SHARE * limit:
        return None
    verb = "over" if size > limit else "near"
    return f"{verb} its {limit:,}-byte limit ({size / limit:.0%})"


@dataclass(frozen=True)
class _Rates:
    """What turns a file's tokens into dollars."""

    conn: sqlite3.Connection
    now: float
    price: float
    everywhere: float


def _file_row(
    rates: _Rates, record: tuple[str, str, str, int | None], history: list[Any]
) -> dict[str, Any]:
    """One file, read live."""
    path, kind, standing, limit = record
    text = _read(path)
    size = None if text is None else len(text.encode())
    tokens = (0 if text is None else _standing_bytes(text, standing)) // BYTES_PER_TOKEN
    calls = (
        _calls_per_day(rates.conn, rates.now, _repo_cwd(path))
        if standing == "in repo"
        else rates.everywhere
    )
    return {
        "path": path,
        "kind": kind,
        "standing": standing,
        "bytes": size,
        "tokens": tokens,
        "usd_per_day": tokens * calls * rates.price / 1e6,
        "warning": None if size is None else _warning(size, limit),
        "history": history,
    }


@panel("context", "Context files", order=50)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Every context file with live size, tokens, $/day and history."""
    rates = _Rates(
        conn,
        filters.until,
        float(_db.meta(conn, "cache_read_usd_per_mtok") or 0.0),
        _calls_per_day(conn, filters.until),
    )
    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path, ts, size, source in conn.execute(
        "SELECT path, ts, bytes, source FROM context_sizes ORDER BY ts"
    ):
        history[path].append({"ts": ts, "bytes": size, "source": source})
    files = [
        _file_row(rates, record, history.get(record[0], []))
        for record in conn.execute(
            "SELECT path, kind, standing, size_limit FROM context_files"
        )
    ]
    files.sort(key=lambda f: -f["usd_per_day"])
    return {
        "files": files,
        "calls_per_day": rates.everywhere,
        "price_per_mtok": rates.price,
    }


def file_detail(conn: sqlite3.Connection, path: str) -> dict[str, Any] | None:
    """Full content and git log of one LISTED file (never an arbitrary path)."""
    listed = conn.execute(
        "SELECT kind FROM context_files WHERE path = ?", (path,)
    ).fetchone()
    if listed is None:
        return None
    folder = str(Path(path).parent)
    try:
        log = subprocess.run(
            [
                GIT,
                "-C",
                folder,
                "log",
                f"-{LOG_LINES}",
                "--format=%h %cs %s",
                "--",
                path,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        ).stdout
    except OSError, subprocess.TimeoutExpired:
        log = ""
    return {
        "path": path,
        "kind": listed[0],
        "content": _read(path),
        "git_log": log.splitlines(),
    }
