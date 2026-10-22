"""Move sessions to a recoverable trash. Nothing here ever unlinks.

Approved by kuhy on 2026-10-22 for the sessions tab. Each transcript
``~/.claude/projects/<dir>/<uuid>.jsonl`` and its sibling ``<uuid>/``
subagent directory move to ``~/.claude/projects-trash/<YYYY-MM-DD>/<dir>/``
with the layout kept, so restoring is moving them back. Every copy of an id
moves (a moved repo leaves one per project dir), or the session would
resurface from the older one.

Everything is checked before the first rename, and any failure refuses the
whole request naming the ids: unknown ids, a transcript written in the last
ten minutes (it may be live -- including the session that sent this
request), a symlink or a path that resolves outside ``~/.claude/projects``,
and a trash slot that is already taken (``rename`` would silently replace it).
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import TYPE_CHECKING

from control_panel import _sysroot
from control_panel.mutations._session_lookup import known_sessions, plural
from control_panel.mutations._session_mark import write_marks
from control_panel.mutations._types import MutationResult
from control_panel.sessions import _api, _marks

if TYPE_CHECKING:
    from pathlib import Path

    from control_panel._runner import CommandRunner
    from control_panel.sessions._parse import Session

# A transcript written this recently may belong to a session still running.
RECENT_SECONDS = 600
TRASH_DISPLAY = "~/.claude/projects-trash"

# The clock, as a seam so tests pin both the recency guard and the trash day.
now = time.time


def trash_root() -> Path:
    """Where deleted transcripts go, one directory per day."""
    return _sysroot.user_path(".claude/projects-trash")


@dataclass(frozen=True, slots=True)
class _Move:
    """One rename: a transcript or a subagent directory."""

    src: Path
    dst: Path


@dataclass(slots=True)
class _Plan:
    """The renames a request needs, and every id that must refuse it."""

    moves: list[_Move]
    recent: list[str]
    escaped: list[str]
    taken: list[str]

    def refusal(self) -> MutationResult | None:
        """Refuse the whole request if any id failed a guard."""
        reasons = [
            f"{label}: {', '.join(dict.fromkeys(ids))}"
            for label, ids in (
                ("written in the last 10 minutes, may be live", self.recent),
                ("a symlink or outside ~/.claude/projects", self.escaped),
                ("already in today's trash", self.taken),
            )
            if ids
        ]
        if not reasons:
            return None
        return MutationResult.refusal(
            f"Nothing moved: {'; '.join(reasons)}.",
            stderr="Every listed session was left exactly where it was.",
        )


def _plan(sessions: list[Session], day_dir: Path) -> _Plan:
    """Check every copy of every session; build the renames if all pass."""
    projects = _api.projects_dir()
    root = projects.resolve()
    cutoff = now() - RECENT_SECONDS
    plan = _Plan(moves=[], recent=[], escaped=[], taken=[])
    for session in sessions:
        for transcript in sorted(projects.glob(f"*/{session.id}.jsonl")):
            subagents = transcript.with_suffix("")
            items = [subagents] if subagents.is_symlink() or subagents.exists() else []
            # The transcript moves last: if anything fails first, the session
            # is still listed rather than half gone.
            items.append(transcript)
            for item in items:
                if item.is_symlink() or not item.resolve().is_relative_to(root):
                    plan.escaped.append(session.id)
                    continue
                dst = day_dir / transcript.parent.name / item.name
                if dst.is_symlink() or dst.exists():
                    plan.taken.append(session.id)
                plan.moves.append(_Move(item, dst))
            if transcript.lstat().st_mtime > cutoff:
                plan.recent.append(session.id)
    return plan


def _move_all(moves: list[_Move]) -> MutationResult | None:
    """Rename in order; on an error, stop and say how far it got."""
    for done, move in enumerate(moves):
        try:
            move.dst.parent.mkdir(parents=True, exist_ok=True)
            move.src.rename(move.dst)
        except OSError as exc:
            return MutationResult.failure(
                f"Moved {done} of {len(moves)} paths; could not move {move.src}.",
                stderr=str(exc),
            )
    return None


def _drop_marks(session_ids: set[str]) -> MutationResult | None:
    """Remove the deleted sessions' manual marks; write only if one existed."""
    path = _api.marks_path()
    marks = _marks.read_marks(path)
    kept = {sid: mark for sid, mark in marks.items() if sid not in session_ids}
    if len(kept) == len(marks):
        return None
    try:
        write_marks(path, kept)
    except OSError as exc:
        return MutationResult.failure(
            f"Moved to the trash, but could not update {path}.", stderr=str(exc)
        )
    return None


def apply(runner: CommandRunner, body: object) -> MutationResult:
    """Move known, idle sessions to today's trash directory."""
    del runner
    sessions = known_sessions(body)
    if isinstance(sessions, MutationResult):
        return sessions
    day = time.strftime("%Y-%m-%d", time.localtime(now()))
    plan = _plan(sessions, trash_root() / day)
    refused = plan.refusal()
    if refused is not None:
        return refused
    session_ids = {s.id for s in sessions}
    failed = _move_all(plan.moves)
    # Forget even after a partial move: a re-parse is cheap, a stale row is not.
    _api.SCANNER.forget(session_ids)
    if failed is None:
        failed = _drop_marks(session_ids)
    if failed is not None:
        return failed
    return MutationResult.success(
        f"Moved {plural(len(sessions))} to {TRASH_DISPLAY}/{day} "
        "(restore by moving them back).",
        stdout="\n".join(f"{m.src} -> {m.dst}" for m in plan.moves)[-4000:],
    )
