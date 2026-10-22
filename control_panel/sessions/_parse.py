"""Read one transcript into a :class:`Session` without reading all of it.

Transcripts reach 65 MB and total ~1.7 GB, so a full parse is out. The file
is memory-mapped and touched in three narrow places:

* the head, forward, until the first real prompt (entrypoint, cwd, title
  fallback);
* the tail, backward line by line, until the last assistant text *and* the
  last real prompt are both known;
* ``rfind`` for the last title record, which Claude Code re-appends near the
  end, so it is usually found within the last few KB.

Lines are filtered on raw bytes before ``json.loads``: every user and
assistant record starts with ``{"parentUuid"`` and friends, never with
``{"type":"``, which is how the bulky ``api-request-blob`` and bookkeeping
records begin.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import mmap
from typing import TYPE_CHECKING, Any

from control_panel.sessions import _status

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

EXCLUDED_ENTRYPOINTS = frozenset({"sdk-cli", "sdk-py"})
TITLE_CHARS = 100
USER_CHARS = 400
ASSISTANT_CHARS = 600
_BOOKKEEPING = b'{"type":"'
_TURN_MARKERS = (b'"type":"user"', b'"type":"assistant"')
# (needle, field): a /rename title beats the generated one, as in /resume.
_TITLE_RECORDS = (
    (b'"type":"custom-title"', "customTitle"),
    (b'"type":"ai-title"', "aiTitle"),
)


@dataclass(frozen=True, slots=True)
class Session:
    """What the dashboard needs to know about one interactive session."""

    id: str
    cwd: str
    title: str
    status: str
    last_ts: str | None
    last_user: str
    last_assistant: str
    mtime_ns: int


@dataclass(slots=True)
class _Tail:
    """What the backward walk has learned so far."""

    assistant: str | None = None
    assistant_ts: str | None = None
    user: str | None = None
    user_ts: str | None = None
    prompt_after_answer: bool = False


def _turn(line: bytes) -> dict[str, Any] | None:
    """Parse a line only if it can be a user or assistant record."""
    if line.startswith(_BOOKKEEPING) or not any(m in line for m in _TURN_MARKERS):
        return None
    try:
        record = json.loads(line)
    except ValueError:
        return None
    return record if isinstance(record, dict) else None


def _forward(mm: mmap.mmap) -> Iterator[bytes]:
    """Yield lines from the start of the map."""
    pos, size = 0, len(mm)
    while pos < size:
        end = mm.find(b"\n", pos)
        end = size if end < 0 else end
        yield mm[pos:end]
        pos = end + 1


def _backward(mm: mmap.mmap) -> Iterator[bytes]:
    """Yield lines from the end of the map, last line first."""
    end = len(mm)
    while end > 0:
        start = mm.rfind(b"\n", 0, end) + 1
        yield mm[start:end]
        end = start - 1


def _head(mm: mmap.mmap) -> tuple[str, str] | None:
    """Return (cwd, first prompt), or None for SDK runs and prompt-less files."""
    cwd = ""
    for line in _forward(mm):
        record = _turn(line)
        if record is None:
            continue
        if record.get("entrypoint") in EXCLUDED_ENTRYPOINTS:
            return None
        cwd = cwd or str(record.get("cwd") or "")
        if record.get("type") == "user":
            prompt = _status.prompt_text(record)
            if prompt:
                return cwd, prompt
    return None


def _tail(mm: mmap.mmap) -> _Tail:
    """Walk back until the last answer and the last prompt are both known."""
    seen = _Tail()
    for line in _backward(mm):
        record = _turn(line)
        if record is None:
            continue
        kind = record.get("type")
        if kind == "assistant" and seen.assistant is None:
            if not record.get("isSidechain"):
                seen.assistant = _status.assistant_text(record)
                seen.assistant_ts = record.get("timestamp")
        elif kind == "user" and seen.user is None:
            prompt = _status.prompt_text(record)
            if prompt:
                seen.user, seen.user_ts = prompt, record.get("timestamp")
                # Met before the answer on a backward walk = typed after it.
                seen.prompt_after_answer = seen.assistant is None
        if seen.assistant is not None and seen.user is not None:
            break
    return seen


def _last_value(mm: mmap.mmap, needle: bytes, field: str) -> str | None:
    """Return ``field`` of the last record of one bookkeeping type."""
    end = len(mm)
    while (hit := mm.rfind(needle, 0, end)) >= 0:
        start = mm.rfind(b"\n", 0, hit) + 1
        stop = mm.find(b"\n", hit)
        try:
            record = json.loads(mm[start : stop if stop >= 0 else len(mm)])
        except ValueError:
            record = None
        if isinstance(record, dict) and isinstance(record.get(field), str):
            return record[field]
        end = start
    return None


def _title(mm: mmap.mmap, first_prompt: str) -> str:
    """The title /resume would show, falling back to the first prompt line."""
    for needle, field in _TITLE_RECORDS:
        title = _last_value(mm, needle, field)
        if title and title.strip():
            return title.strip()
    first_line = first_prompt.strip().splitlines()[0] if first_prompt.strip() else ""
    if len(first_line) > TITLE_CHARS:
        return first_line[: TITLE_CHARS - 1] + "…"
    return first_line


def _status_of(seen: _Tail) -> str:
    """Classify the last answer, unless the user typed after it."""
    if seen.assistant is None:
        return _status.UNTAGGED
    interrupted = seen.prompt_after_answer
    if interrupted and seen.user_ts and seen.assistant_ts:
        interrupted = seen.user_ts > seen.assistant_ts
    return _status.UNTAGGED if interrupted else _status.classify(seen.assistant)


def read_session(path: Path) -> Session | None:
    """Read one transcript; None when it is not an interactive session."""
    with path.open("rb") as handle:
        stat = path.stat()
        if stat.st_size == 0:
            return None
        with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            head = _head(mm)
            if head is None:
                return None
            cwd, first_prompt = head
            seen = _tail(mm)
            title = _title(mm, first_prompt)
    stamps = [ts for ts in (seen.assistant_ts, seen.user_ts) if isinstance(ts, str)]
    return Session(
        id=path.stem,
        cwd=cwd,
        title=title,
        status=_status_of(seen),
        last_ts=max(stamps) if stamps else None,
        last_user=(seen.user or first_prompt)[:USER_CHARS],
        last_assistant=(seen.assistant or "")[-ASSISTANT_CHARS:],
        mtime_ns=stat.st_mtime_ns,
    )
