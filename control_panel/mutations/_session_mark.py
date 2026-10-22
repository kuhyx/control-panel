"""Mark a session done by hand, or clear that mark.

Approved by kuhy on 2026-10-22 for the sessions tab. The store is the
dashboard's own file (``~/.claude/session-status.json``), not a guard's, so
there is no ratchet to defer to: the only rules are a known id and a known
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

from control_panel.mutations._session_lookup import known_session
from control_panel.mutations._types import MutationResult
from control_panel.sessions import _api, _marks

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner


# The clock, as a seam so tests get a fixed ``at``.
now = time.time


def _write_atomically(path: Path, marks: dict[str, Any]) -> None:
    """Replace ``path`` with ``marks`` in one rename."""
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
    """Set ``mark`` ("done") on a known session, or clear it with null."""
    del runner
    if not isinstance(body, dict):
        return MutationResult.failure("Expected a JSON object.")
    mark = body.get("mark")
    if mark is not None and mark not in _marks.MARKS:
        return MutationResult.failure(
            f"Expected 'mark' to be one of {list(_marks.MARKS)} or null."
        )
    session = known_session(body)
    if isinstance(session, MutationResult):
        return session
    path = _api.marks_path()
    marks = _marks.read_marks(path)
    if mark is None:
        marks.pop(session.id, None)
    else:
        marks[session.id] = {"mark": mark, "at": int(now())}
    try:
        _write_atomically(path, marks)
    except OSError as exc:
        return MutationResult.failure(f"Could not write {path}.", stderr=str(exc))
    verb = f"marked {mark}" if mark else "unmarked"
    return MutationResult.success(f"{session.title or session.id} {verb}.")
