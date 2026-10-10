"""Who holds a declared dashboard's port -- and is it the subsystem itself?

Found by running it: mangatl declared ``127.0.0.1:8780`` while Anki's sync
server (``anki-syncserver.service``) held that port. mangatl is on demand, so
its dashboard is never probed, its units read ARMED, and the panel showed a
healthy subsystem whose link opened somebody else's 404.

Ownership comes from the listening process's cgroup, read from
``/proc/<pid>/cgroup`` -- a file read, not a fork. systemd puts every process a
unit starts in that unit's cgroup (children included), and Docker puts a
container's processes in ``docker-<id>.scope``, so the cgroup names the unit
or container directly.

A clash is reported only when the owner is **visible and attributable and
foreign**:

* ``ss -p`` run as this user names no process for root's ``docker-proxy`` or
  for other users' sockets (8088, 8089, 8282 ...): owner not visible, no clash.
* A process started by hand sits in a ``session-N.scope`` or ``app-*.scope``;
  systemd itself (socket activation) sits in ``init.scope``. None of those say
  which subsystem it belongs to -- book-guard's 8773 is served by its desktop
  app from a session scope -- so they are never called foreign.
"""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from control_panel import _sysroot, _unknown
from control_panel._types import Scope

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from control_panel._manifest import ManifestEntry

_PID = re.compile(r"pid=(\d+)")
_CMDLINE_CHARS = 80
# docker (systemd cgroup driver) and podman name a container's scope this way.
_CONTAINER_SCOPE = re.compile(r"^(?:docker|libpod)-([0-9a-f]{12,64})\.scope$")
_CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
# Listener addresses that accept a connection to each loopback dashboard host.
# The wildcard is spelled via ipaddress: this module reads `ss`, it binds nothing.
_ANY_V4 = str(ipaddress.IPv4Address(0))
_V4 = frozenset({"127.0.0.1", _ANY_V4, "*", "[::]", "[::ffff:127.0.0.1]"})
_V6 = frozenset({"[::1]", "[::]", "*"})
_SERVES = {"127.0.0.1": _V4, "::1": _V6, "localhost": _V4 | _V6}

# port -> [(listen address, pids)]
Listeners = dict[int, list[tuple[str, tuple[int, ...]]]]


@dataclass(frozen=True, slots=True)
class Owner:
    """An attributable owner of a listening socket."""

    kind: str  # "unit" or "container"
    name: str
    pid: int
    scope: Scope | None = None
    cmdline: str = ""

    def describe(self) -> str:
        """Name the owner for a reason line: unit or container, pid, command."""
        what = self.name if self.kind == "unit" else f"container {self.name}"
        command = f" {self.cmdline}" if self.cmdline else ""
        return f"{what} (pid {self.pid}{command})"


def parse_listeners(stdout: str) -> Listeners:
    """Map each port in ``ss -ltnpH`` output to its addresses and owner pids.

    Every pid on the line is kept: one socket can be shared by several
    processes (8141 lists pid 7747 twice), and any of them may be foreign.
    """
    found: Listeners = {}
    for address, port, line in _unknown.ss_endpoints(stdout):
        # "127.0.0.1%lo" style interface suffixes are not part of the address.
        bare = address.split("%", 1)[0]
        pids = tuple(dict.fromkeys(int(pid) for pid in _PID.findall(line)))
        found.setdefault(port, []).append((bare, pids))
    return found


def attribute(cgroup: str) -> tuple[str, str, Scope | None] | None:
    """Classify a ``/proc/<pid>/cgroup`` body into (kind, name, scope), or None.

    Walks the cgroup v2 path from the leaf upwards, so a unit that delegates
    sub-cgroups (``foo.service/payload``) is still found. Returns None for
    anything that does not name one unit or container: sessions, ``app-*``
    scopes, ``init.scope`` and the user manager itself.
    """
    path = next(
        (line[3:] for line in cgroup.splitlines() if line.startswith("0::")), ""
    )
    parts = [part for part in path.split("/") if part]
    for index in range(len(parts) - 1, -1, -1):
        part = parts[index]
        container = _CONTAINER_SCOPE.match(part)
        if container:
            return "container", container.group(1), None
        if _CONTAINER_ID.match(part) and index > 0 and parts[index - 1] == "docker":
            return "container", part, None
        if part.endswith((".scope", ".slice")) or part.startswith("user@"):
            return None
        if part.endswith(".service"):
            in_user_manager = any(p.startswith("user@") for p in parts[:index])
            return "unit", part, Scope.USER if in_user_manager else Scope.SYSTEM
    return None


def read_proc(pid: int, name: str) -> str | None:
    """Read ``/proc/<pid>/<name>`` under the sysroot, or None if it is gone."""
    try:
        raw = _sysroot.sysroot_path(f"/proc/{pid}/{name}").read_bytes()
    except OSError:
        return None
    return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()


class OwnerResolver:
    """Resolve pids to attributable owners, reading each pid at most once."""

    def __init__(
        self,
        container_ids: Mapping[str, str],
        read: Callable[[int, str], str | None] = read_proc,
    ) -> None:
        """Store ``container_ids`` (container name -> short id) and the reader."""
        self._ids = dict(container_ids)
        self._read = read
        self._cache: dict[int, Owner | None] = {}

    def __call__(self, pid: int) -> Owner | None:
        """Return the owner of ``pid``, or None when it cannot be attributed."""
        if pid not in self._cache:
            self._cache[pid] = self._resolve(pid)
        return self._cache[pid]

    def _resolve(self, pid: int) -> Owner | None:
        cgroup = self._read(pid, "cgroup")
        # A vanished pid or an unreadable cgroup: not visible, so no verdict.
        found = attribute(cgroup) if cgroup else None
        if found is None:
            return None
        kind, name, scope = found
        if kind == "container":
            matched = next(
                (
                    n
                    for n, short in self._ids.items()
                    if short and name.startswith(short)
                ),
                None,
            )
            if matched is None:
                return None
            name = matched
        cmdline = (self._read(pid, "cmdline") or "")[:_CMDLINE_CHARS]
        return Owner(kind=kind, name=name, pid=pid, scope=scope, cmdline=cmdline)


def _loopback_port(url: str) -> tuple[str, int] | None:
    """Return (host, port) for a loopback http(s) URL, else None."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if host not in _SERVES:
        return None
    try:
        port = parts.port
    except ValueError:
        return None
    if port is None:
        port = 443 if parts.scheme == "https" else 80
    return host, port


def _owns(entry: ManifestEntry, owner: Owner) -> bool:
    """Whether ``owner`` is one of the units or containers ``entry`` declares."""
    if owner.kind == "container":
        return owner.name in {c.name for c in entry.live.containers}
    return (owner.name, owner.scope) in {(u.name, u.scope) for u in entry.units}


def clash(
    entry: ManifestEntry,
    url: str,
    listeners: Listeners,
    resolve: Callable[[int], Owner | None],
) -> str | None:
    """Describe a foreign owner of ``url``'s loopback port, or None.

    None when the dashboard is not on loopback, nothing listens, the owner is
    invisible or unattributable, or the owner belongs to ``entry``.
    """
    target = _loopback_port(url)
    if target is None:
        return None
    host, port = target
    for address, pids in listeners.get(port, ()):
        if address not in _SERVES[host]:
            continue
        for pid in pids:
            owner = resolve(pid)
            if owner is not None and not _owns(entry, owner):
                return f"port {port} held by {owner.describe()}"
    return None


def listening(url: str, listeners: Listeners) -> bool | None:
    """Whether anything listens on ``url``'s loopback port; None if not loopback."""
    target = _loopback_port(url)
    if target is None:
        return None
    host, port = target
    return any(address in _SERVES[host] for address, _ in listeners.get(port, ()))
