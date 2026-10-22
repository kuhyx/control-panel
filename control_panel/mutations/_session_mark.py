"""Mark sessions done by hand, or clear that mark.

Approved by kuhy on 2026-10-22 for the sessions tab. The store is the
dashboard's own file (``~/.claude/session-status.json``), not a guard's, so
there is no ratchet to defer to: the only rules are known ids and a known
mark. The write is tmp + rename, so a crash mid-write leaves the old file.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import TYPE_CHECKING, Any

from control_panel.mutations._session_lookup import is_bulk, known_sessions, plural
from control_panel.mutations._types import MutationResult
from control_panel.sessions import _api, _marks

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner


# The clock, as a seam so tests get a fixed ``at``.
now = time.time


def write_marks(path: Path, marks: dict[str, Any]) -> None:
    """Replace ``path`` with ``marks`` in one rename.

    Shared with :mod:`._session_delete`, which drops the marks of the
    sessions it moves to the trash.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(marks, handle, indent=1, sort_keys=True)
            handle.write("\n")
        Path(tmp).replace(path)
    except BaseException:
        with contextlib.suppress(OSError):
            Path(tmp).unlink()
        raise


def apply(runner: CommandRunner, body: object) -> MutationResult:
    """Set ``mark`` ("done") on known sessions, or clear it with null."""
    del runner
    if not isinstance(body, dict):
        return MutationResult.failure("Expected a JSON object.")
    mark = body.get("mark")
    if mark is not None and mark not in _marks.MARKS:
        return MutationResult.failure(
            f"Expected 'mark' to be one of {list(_marks.MARKS)} or null."
        )
    sessions = known_sessions(body)
    if isinstance(sessions, MutationResult):
        return sessions
    path = _api.marks_path()
    marks = _marks.read_marks(path)
    for session in sessions:
        if mark is None:
            marks.pop(session.id, None)
        else:
            marks[session.id] = {"mark": mark, "at": int(now())}
    try:
        write_marks(path, marks)
    except OSError as exc:
        return MutationResult.failure(f"Could not write {path}.", stderr=str(exc))
    if is_bulk(body):
        count = plural(len(sessions))
        return MutationResult.success(
            f"Marked {count} {mark}." if mark else f"Unmarked {count}."
        )
    session = sessions[0]
    verb = f"marked {mark}" if mark else "unmarked"
    return MutationResult.success(f"{session.title or session.id} {verb}.")
