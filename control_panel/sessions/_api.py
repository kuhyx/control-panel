"""``GET /api/sessions``: every interactive session, open ones first.

Also the lookup the session mutations use, so that "is this id real, and
where does it live?" is answered from the same scan the user is looking at,
never from the request.
"""

from __future__ import annotations

from http import HTTPStatus
import os
from pathlib import PurePosixPath
import time
from typing import TYPE_CHECKING, Any
import uuid

from control_panel import _sysroot
from control_panel.sessions._marks import read_marks
from control_panel.sessions._scan import Scanner

if TYPE_CHECKING:
    from pathlib import Path

    from control_panel.sessions._parse import Session

__all__ = ["SCANNER", "Scanner", "canonical_id", "find", "marks_path", "route"]

# One process-wide cache: GETs and mutations share it, so a resume right after
# a page load re-reads nothing.
SCANNER = Scanner()
# Open sessions in the order they need attention; everything done after them.
_GROUP = {"needs_action": 0, "question": 1, "untagged": 2, "running": 3}
_DONE_GROUP = len(_GROUP)
_DONE_STATUSES = frozenset({"done", "continuing"})


def projects_dir() -> Path:
    """Where Claude Code keeps one directory of transcripts per project."""
    return _sysroot.user_path(".claude/projects")


def marks_path() -> Path:
    """The manual-mark store, next to Claude Code's own state."""
    return _sysroot.user_path(".claude/session-status.json")


def canonical_id(value: object) -> str | None:
    """Return ``value`` if it is a UUID in canonical form, else None.

    ``uuid.UUID`` alone also accepts braces, ``urn:uuid:``, upper case and
    no hyphens; only the spelling Claude Code writes is an id here, because
    the id ends up inside a shell command line.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        return None
    return value if str(parsed) == value else None


def find(session_id: str) -> Session | None:
    """Look an id up in a (warm, cheap) rescan of the transcripts."""
    return SCANNER.scan(projects_dir())[0].get(session_id)


def _quote(text: str) -> str:
    """Single-quote for a POSIX shell, always, as the contract shows."""
    return "'" + text.replace("'", "'\\''") + "'"


def _project(cwd: str) -> str:
    """The short project name: the cwd's basename, or ``~`` for home."""
    home = os.environ.get("HOME", "").rstrip("/")
    if cwd.rstrip("/") == home:
        return "~"
    return PurePosixPath(cwd.rstrip("/")).name


def _row(session: Session, mark: dict[str, Any] | None) -> dict[str, Any]:
    """Render one session in the frontend's JSON contract."""
    manual = mark.get("mark") if mark else None
    return {
        "id": session.id,
        "cwd": session.cwd,
        "project": _project(session.cwd),
        "title": session.title,
        "status": session.status,
        "done": session.status in _DONE_STATUSES or manual == "done",
        "manual_mark": manual,
        "last_ts": session.last_ts,
        "last_user": session.last_user,
        "last_assistant": session.last_assistant,
        "resume_command": f"cd {_quote(session.cwd)} && claude --resume {session.id}",
    }


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group by urgency, newest first within each group."""
    rows = sorted(rows, key=lambda r: r["last_ts"] or "", reverse=True)
    return sorted(
        rows, key=lambda r: _DONE_GROUP if r["done"] else _GROUP.get(r["status"], 0)
    )


def route(segments: list[str], query: str) -> tuple[HTTPStatus, dict[str, Any]]:
    """Serve the whole session list; there are no sub-resources."""
    del query
    if any(segments):
        return HTTPStatus.NOT_FOUND, {"error": "expected /api/sessions"}
    started = time.perf_counter()
    sessions, scanned = SCANNER.scan(projects_dir())
    marks = read_marks(marks_path())
    rows = _ordered([_row(s, marks.get(s.id)) for s in sessions.values()])
    elapsed = (time.perf_counter() - started) * 1000
    return HTTPStatus.OK, {
        "sessions": rows,
        "scanned": scanned,
        "scan_ms": round(elapsed, 1),
    }
