"""Bounded log tails for declared units and containers.

Only things a manifest entry declares can be read, so a request path cannot
turn this into "read any unit's journal". Both sources are read without sudo:
this user is in ``wheel``, which journald's ACLs grant read access to the
system journal, and in ``docker``, which allows ``docker logs``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from control_panel._types import Scope

if TYPE_CHECKING:
    from control_panel._manifest import ManifestEntry
    from control_panel._runner import CommandRunner

DEFAULT_LINES = 100
MAX_LINES = 1000
DOCKER = "docker"


def clamp(lines: int) -> int:
    """Keep a requested line count inside ``1..MAX_LINES``."""
    return max(1, min(lines, MAX_LINES))


def is_declared(entries: tuple[ManifestEntry, ...], source: str, name: str) -> bool:
    """Whether ``name`` is a declared unit in scope ``source``, or a container."""
    for entry in entries:
        if source == DOCKER and any(c.name == name for c in entry.live.containers):
            return True
        if any(u.name == name and u.scope == source for u in entry.units):
            return True
    return False


def argv_for(source: str, name: str, lines: int) -> tuple[str, ...]:
    """Build the read-only command for one source."""
    if source == DOCKER:
        return ("docker", "logs", "--timestamps", "--tail", str(lines), name)
    scope = ("--user",) if source == Scope.USER else ()
    return (
        "journalctl",
        *scope,
        "--unit",
        name,
        "--lines",
        str(lines),
        "--no-pager",
        "--output",
        "short-iso",
    )


def read(
    runner: CommandRunner,
    entries: tuple[ManifestEntry, ...],
    source: str,
    name: str,
    lines: int,
) -> dict[str, Any] | None:
    """Tail one declared source, or None when it is not declared."""
    if not is_declared(entries, source, name):
        return None
    count = clamp(lines)
    result = runner.run(argv_for(source, name, count))
    tail = result.stdout.splitlines()
    if source == DOCKER:
        # `docker logs` replays the container's stderr on our stderr, so both
        # streams are the log. --timestamps prefixes RFC 3339 times, and a
        # stable sort on them restores the order the two pipes lost.
        tail = sorted(tail + result.stderr.splitlines())
    return {
        "source": source,
        "name": name,
        "lines": tail[-count:],
        "ok": result.ok,
        "error": "" if result.ok else (result.error or result.stderr.strip()),
    }
