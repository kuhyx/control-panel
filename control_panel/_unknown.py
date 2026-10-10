"""What is running that no manifest entry accounts for.

A declared manifest can only report what someone remembered to declare, so it
is blind to the server started last week. This module is the other half: every
TCP listener whose port no entry claims, and every unit file in the user's own
systemd directory that no entry names. Ports are matched rather than
addresses, because a server bound to ``0.0.0.0`` is declared as ``127.0.0.1``.

``ss -ltnpH`` only names processes this user owns; root and container
listeners come back without one, which is reported rather than escalated.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from control_panel import _sysroot
from control_panel._live_types import Listener, UndeclaredUnit

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from control_panel._manifest import IgnoredListener, ManifestEntry
    from control_panel._runner import CommandRunner

SS_ARGV = ("ss", "-ltnpH")
PORT_RANGE = "/proc/sys/net/ipv4/ip_local_port_range"
DEFAULT_EPHEMERAL_FLOOR = 32768
USER_UNIT_DIR = ".config/systemd/user"
_UNIT_SUFFIXES = (".service", ".timer", ".path", ".socket")
_PROCESS = re.compile(r'users:\(\("([^"]+)"')
_PID = re.compile(r"pid=(\d+)")
_LOOPBACK = frozenset({"127.0.0.1", "[::1]"})
_LOCAL_FIELD = 3
_CMDLINE_CHARS = 80


def _port_of(target: str) -> int | None:
    """Extract the port from a URL or ``host:port`` probe target."""
    if "://" in target:
        parts = urlsplit(target)
        if parts.port is not None:
            return parts.port
        return 443 if parts.scheme == "https" else 80
    _, _, port = target.rpartition(":")
    return int(port) if port.isdigit() else None


def declared_ports(entries: tuple[ManifestEntry, ...]) -> frozenset[int]:
    """Every port a probe or dashboard in the manifest names."""
    targets = [p.target for e in entries for p in e.live.probes]
    targets += [d.url for e in entries for d in e.live.dashboards]
    return frozenset(p for p in map(_port_of, targets) if p is not None)


def _process(line: str) -> str:
    """Name the listener's process: its command line when readable.

    ``python`` alone says nothing -- issue-dashboard and signal-bot are both
    ``python`` -- so the command line is preferred. Root and container
    processes are unreadable and fall back to ss's name, or nothing.
    """
    pid = _PID.search(line)
    if pid is not None:
        try:
            raw = _sysroot.sysroot_path(f"/proc/{pid.group(1)}/cmdline").read_bytes()
        except OSError:
            raw = b""
        text = raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
        if text:
            return text[:_CMDLINE_CHARS]
    name = _PROCESS.search(line)
    return name.group(1) if name else ""


def ss_endpoints(stdout: str) -> Iterator[tuple[str, int, str]]:
    """Yield ``(address, port, line)`` for each socket in ``ss -ltnpH`` output."""
    for line in stdout.splitlines():
        fields = line.split()
        if len(fields) <= _LOCAL_FIELD:
            continue
        address, _, port = fields[_LOCAL_FIELD].rpartition(":")
        if port.isdigit():
            yield address, int(port), line


def parse_listeners(stdout: str) -> list[Listener]:
    """Parse ``ss -ltnpH`` into one record per (address, port)."""
    found: dict[tuple[str, int], Listener] = {}
    for address, port, line in ss_endpoints(stdout):
        if (address, port) not in found:
            found[address, port] = Listener(
                address=address, port=port, process=_process(line)
            )
    return sorted(found.values(), key=lambda item: (item.port, item.address))


def ephemeral_floor() -> int:
    """The lowest port the kernel hands out by itself (32768 on Arch)."""
    try:
        first = _sysroot.sysroot_path(PORT_RANGE).read_text(encoding="ascii").split()[0]
    except OSError, IndexError:
        return DEFAULT_EPHEMERAL_FLOOR
    return int(first) if first.isdigit() else DEFAULT_EPHEMERAL_FLOOR


def _is_noise(item: Listener, floor: int) -> bool:
    """A loopback listener on a kernel-assigned port: Steam, containerd.

    Those ports change every run, so they can never be declared, and on
    loopback nothing else can reach them. A kernel-assigned port open to the
    network still shows -- that one is worth knowing about.
    """
    return item.port >= floor and item.address in _LOOPBACK


def unknown_listeners(
    runner: CommandRunner,
    entries: tuple[ManifestEntry, ...],
    ignored: tuple[IgnoredListener, ...],
    own_port: int,
) -> list[Listener]:
    """Listeners on ports neither declared, ignored, ours, nor kernel noise."""
    result = runner.run(SS_ARGV)
    if not result.ok:
        return []
    known = declared_ports(entries) | {item.port for item in ignored} | {own_port}
    floor = ephemeral_floor()
    return [
        item
        for item in parse_listeners(result.stdout)
        if item.port not in known and not _is_noise(item, floor)
    ]


def _is_own(path: Path) -> bool:
    """A real unit file, not a symlink to a vendor unit under ``/usr``.

    ``dbus.service`` here is a symlink to ``/usr/lib/.../dbus-broker.service``:
    the distribution's unit under an alias, not part of this fleet.
    """
    if not path.is_file():
        return False
    return not (path.is_symlink() and str(path.resolve()).startswith("/usr/"))


def undeclared_units(entries: tuple[ManifestEntry, ...]) -> list[UndeclaredUnit]:
    """User unit files in ``~/.config/systemd/user`` that no entry declares.

    Only that directory: vendor units (pipewire, gpg-agent) are the
    distribution's business, not this fleet's.
    """
    directory = _sysroot.user_path(USER_UNIT_DIR)
    try:
        names = sorted(
            path.name
            for path in directory.iterdir()
            if path.name.endswith(_UNIT_SUFFIXES) and _is_own(path)
        )
    except OSError:
        return []
    declared = {u.name for e in entries for u in e.units if u.scope == "user"}
    return [UndeclaredUnit(name=n, scope="user") for n in names if n not in declared]
