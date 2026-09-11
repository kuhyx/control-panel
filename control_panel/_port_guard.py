"""Decide what to do when the fixed port is already taken.

This deliberately inverts ``~/src/todo/lib/desktop/port_guard.dart``. todo may reap
the process holding its port because the port is immovable -- the browser keys
``localStorage`` and IndexedDB by origin, so a fallback port would present an
empty, logged-out app. control-panel holds no origin-keyed state, so it has no
such excuse: it identifies the owner and **refuses to start**.

A read-only dashboard that kills a process to take a port would be the single
most destructive thing in a package whose entire purpose is to observe. The
test suite asserts that no signal is ever sent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner

# errno 98: the port is bound by someone else.
EADDRINUSE = 98
_PID_PATTERN = re.compile(r"pid=(\d+)")
# `ss -tlnp` columns: State Recv-Q Send-Q Local-Address:Port ...
_LOCAL_ADDRESS_FIELD = 3


@dataclass(frozen=True, slots=True)
class PortOwner:
    """Whoever currently holds the port, as far as we could tell."""

    pid: int | None
    exe: str | None
    cmdline: str | None

    def describe(self) -> str:
        """Render a one-line description for the refusal message."""
        if self.pid is None:
            return "an unidentified process (ss reported no pid)"
        parts = [f"pid {self.pid}"]
        if self.exe:
            parts.append(self.exe)
        if self.cmdline:
            parts.append(f"({self.cmdline})")
        return " ".join(parts)


def _listener_pid(stdout: str, port: int) -> int | None:
    """Extract the pid listening on ``port`` from ``ss -tlnp`` output."""
    for line in stdout.splitlines():
        fields = line.split()
        # Field 3 is Local Address:Port. Match on the suffix so both 127.0.0.1
        # and [::1] forms are caught.
        if len(fields) <= _LOCAL_ADDRESS_FIELD:
            continue
        if not fields[_LOCAL_ADDRESS_FIELD].endswith(f":{port}"):
            continue
        match = _PID_PATTERN.search(line)
        if match:
            return int(match.group(1))
    return None


def _read_proc(pid: int, name: str) -> str | None:
    """Read one /proc entry for ``pid``, or None if it cannot be read."""
    try:
        if name == "exe":
            # readlink, not resolve: resolve() is non-strict by default and
            # happily returns "/proc/<dead pid>/exe" unchanged, so a vanished
            # process would be reported as if it had that path as its binary.
            return str(Path(f"/proc/{pid}/exe").readlink())
        raw = Path(f"/proc/{pid}/{name}").read_bytes()
    except OSError:
        return None
    return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip() or None


def identify_owner(runner: CommandRunner, port: int) -> PortOwner:
    """Identify the process holding ``port``, without touching it."""
    result = runner.run(("ss", "-tlnp"))
    pid = _listener_pid(result.stdout, port) if result.ok else None
    if pid is None:
        return PortOwner(pid=None, exe=None, cmdline=None)
    return PortOwner(
        pid=pid, exe=_read_proc(pid, "exe"), cmdline=_read_proc(pid, "cmdline")
    )


def refusal_message(runner: CommandRunner, port: int) -> str:
    """Build the message shown when the port is taken.

    Naming the owner is the whole value: "port in use" sends you to `ss`,
    whereas "held by pid 912 /usr/bin/python3" ends the investigation.
    """
    owner = identify_owner(runner, port)
    return (
        f"Port {port} is already in use by {owner.describe()}.\n"
        f"control-panel will not stop it -- this dashboard never touches other "
        f"processes.\nStop it yourself, or pass --port to use a different one."
    )
