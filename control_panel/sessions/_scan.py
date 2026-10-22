"""Walk every project directory, re-reading only transcripts that changed.

The cache key is ``(mtime_ns, size)`` per path, so a warm scan costs one
``stat`` per file and nothing else. Only top-level ``*.jsonl`` files count:
the ``<uuid>/`` subdirectories beside them hold subagent transcripts, which
are not sessions anyone resumes.
"""

from __future__ import annotations

import os
from pathlib import Path
import threading

from control_panel.sessions import _parse

_CacheKey = tuple[int, int]


class Scanner:
    """An in-process cache of parsed transcripts, keyed by file version."""

    def __init__(self) -> None:
        """Start empty; the first scan is the cold one."""
        self._cache: dict[str, tuple[_CacheKey, _parse.Session | None]] = {}
        # The HTTP server is threaded, and a resume mutation can race a GET.
        self._lock = threading.Lock()

    def _read(self, path: str, key: _CacheKey) -> _parse.Session | None:
        """Return the cached parse for this file version, or parse it now."""
        cached = self._cache.get(path)
        if cached is not None and cached[0] == key:
            return cached[1]
        try:
            session = _parse.read_session(Path(path))
        except OSError, ValueError:
            # Unreadable now is not unreadable forever: cache it against this
            # version only, so the next write retries it.
            session = None
        self._cache[path] = (key, session)
        return session

    def cached(self) -> list[str]:
        """The transcript paths this cache currently holds a parse for."""
        with self._lock:
            return list(self._cache)

    def forget(self, session_ids: set[str]) -> None:
        """Drop every cached transcript of these sessions, in memory only.

        The delete mutation calls this after moving the files away, so no
        reader is ever handed a session whose transcript is in the trash.
        """
        with self._lock:
            for path in [p for p in self._cache if Path(p).stem in session_ids]:
                del self._cache[path]

    def scan(self, projects: Path) -> tuple[dict[str, _parse.Session], int]:
        """Return interactive sessions by id, and how many files were examined.

        A session id that appears in two project directories (a moved repo)
        keeps the most recently written transcript.
        """
        with self._lock:
            found: dict[str, _parse.Session] = {}
            seen: set[str] = set()
            for path, key in _transcripts(projects):
                seen.add(path)
                session = self._read(path, key)
                if session is None:
                    continue
                previous = found.get(session.id)
                if previous is None or previous.mtime_ns < session.mtime_ns:
                    found[session.id] = session
            for gone in self._cache.keys() - seen:
                del self._cache[gone]
            return found, len(seen)


def _transcripts(projects: Path) -> list[tuple[str, _CacheKey]]:
    """List ``(path, (mtime_ns, size))`` for every top-level transcript."""
    out: list[tuple[str, _CacheKey]] = []
    try:
        with os.scandir(projects) as found:
            folders = [e.path for e in found if e.is_dir(follow_symlinks=False)]
    except OSError:
        return out
    for folder in folders:
        # One unreadable or vanishing project dir skips that dir, not the scan.
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if entry.name.endswith(".jsonl") and entry.is_file():
                        stat = entry.stat()
                        out.append((entry.path, (stat.st_mtime_ns, stat.st_size)))
        except OSError:
            continue
    return out
