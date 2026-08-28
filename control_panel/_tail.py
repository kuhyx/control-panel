"""Bounded reads of log files that are far too large to open.

``/var/log/hosts-file-monitor.log`` is 57 MB, ``shutdown-timer-monitor.log``
10 MB and ``periodic-system-maintenance.log`` 7.4 MB. Nothing here ever reads a
whole file: it seeks to the last window and discards the first, probably
partial, line.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from control_panel import _sysroot

# 64 KiB is comfortably more than 2000 lines of these logs and small enough
# that reading it costs nothing.
TAIL_WINDOW = 65536
DEFAULT_LINES = 200
MAX_LINES = 2000
# Above this, a log is not merely large, it is unrotated and growing forever.
UNROTATED_DANGER_BYTES = 32 * 1024 * 1024
UNROTATED_WARN_BYTES = 4 * 1024 * 1024
LOGROTATE_DIR = "/etc/logrotate.d"


@dataclass(frozen=True, slots=True)
class LogStat:
    """Metadata about a log file, gathered without reading its contents."""

    path: str
    exists: bool
    size: int | None = None
    mtime: str | None = None
    rotated: bool | None = None


def _resolve(path: str) -> Path:
    """Resolve a declared log path, expanding a leading ``~``."""
    if path.startswith("~/"):
        return _sysroot.user_path(path[2:])
    return _sysroot.sysroot_path(path)


def has_logrotate_entry(path: str) -> bool:
    """Report whether any logrotate config mentions this file's basename.

    A substring match on the basename is deliberately loose: logrotate configs
    routinely use globs, and a false "yes" here only downgrades a warning,
    whereas a false "no" would cry wolf about a file that is actually rotated.
    """
    name = Path(path).name
    directory = _sysroot.sysroot_path(LOGROTATE_DIR)
    try:
        # Sorted so the answer does not depend on directory order.
        configs = sorted(directory.iterdir())
    except OSError:
        return False
    for config in configs:
        try:
            if name in config.read_text(encoding="utf-8", errors="replace"):
                return True
        except OSError:
            continue
    return False


def describe(path: str) -> LogStat:
    """Stat a log file, never opening it."""
    resolved = _resolve(path)
    try:
        info = resolved.stat()
    except OSError:
        return LogStat(path=path, exists=False)
    return LogStat(
        path=path,
        exists=True,
        size=info.st_size,
        mtime=datetime.fromtimestamp(info.st_mtime, tz=UTC).isoformat(),
        rotated=has_logrotate_entry(path),
    )


@dataclass(frozen=True, slots=True)
class TailResult:
    """The last ``n`` lines of a log, plus how much was skipped."""

    lines: tuple[str, ...]
    truncated: bool
    total_bytes: int | None
    error: str | None = None


def tail(path: str, lines: int = DEFAULT_LINES) -> TailResult:
    """Return at most ``lines`` trailing lines, reading at most 64 KiB."""
    capped = max(1, min(lines, MAX_LINES))
    resolved = _resolve(path)
    try:
        size = resolved.stat().st_size
        with resolved.open("rb") as handle:
            handle.seek(max(0, size - TAIL_WINDOW))
            chunk = handle.read(TAIL_WINDOW)
    except OSError as exc:
        return TailResult(lines=(), truncated=False, total_bytes=None, error=str(exc))
    windowed = size > TAIL_WINDOW
    if windowed:
        # The seek almost certainly landed mid-line; drop that fragment rather
        # than render half a log entry as if it were a whole one.
        _, _, chunk = chunk.partition(b"\n")
    text = chunk.decode("utf-8", errors="replace").splitlines()
    return TailResult(
        lines=tuple(text[-capped:]),
        truncated=windowed or len(text) > capped,
        total_bytes=size,
    )
