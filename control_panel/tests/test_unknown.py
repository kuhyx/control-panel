from __future__ import annotations

from ipaddress import IPv4Address
from typing import TYPE_CHECKING

from control_panel import _unknown
from control_panel._live_types import Listener
from control_panel._manifest import ManifestProbe
from control_panel._manifest_live import IgnoredListener, ManifestDashboard
from control_panel._types import Scope
from control_panel.tests import _fixture_fleet as fleet
from control_panel.tests._fixture_runner import FakeRunner, ok

if TYPE_CHECKING:
    from pathlib import Path

# 0.0.0.0 built rather than typed: this is test data describing what ss
# prints, not a bind, and the literal trips bandit's S104.
ANY = str(IPv4Address(0))
SS = (
    'LISTEN 0 5 127.0.0.1:8140 0.0.0.0:* users:(("python",pid=4242,fd=6))\n'
    'LISTEN 0 5 127.0.0.1:8798 0.0.0.0:* users:(("python",pid=4243,fd=6))\n'
    'LISTEN 0 5 [::1]:8798 [::]:* users:(("python",pid=4243,fd=7))\n'
    f"LISTEN 0 5 {ANY}:22 {ANY}:*\n"
    "LISTEN 0 5 127.0.0.1:44375 0.0.0.0:*\n"
    f"LISTEN 0 5 {ANY}:52736 {ANY}:*\n"
    "LISTEN 0 5 127.0.0.1:8760 0.0.0.0:*\n"
    "LISTEN 0 5 127.0.0.1:443 0.0.0.0:*\n"
    "LISTEN 0 5 *:http 0.0.0.0:*\n"
    "garbage"
)
ENTRIES = (
    fleet.live_entry(
        probes=(
            ManifestProbe(kind="tcp", target="127.0.0.1:9"),
            ManifestProbe("tcp", "bad"),
        ),
        dashboards=(
            ManifestDashboard(label="UI", url="http://127.0.0.1:8140/"),
            ManifestDashboard(label="Pub", url="https://kuhy.duckdns.org/"),
            ManifestDashboard(label="Plain", url="http://example.org/"),
        ),
        units=(
            fleet.service("declared.service"),
            fleet.service("sys.service", Scope.SYSTEM),
        ),
    ),
)


def _proc(sysroot: Path, pid: int, cmdline: bytes) -> None:
    path = sysroot / f"proc/{pid}/cmdline"
    path.parent.mkdir(parents=True)
    path.write_bytes(cmdline)


def test_declared_ports_cover_urls_and_targets() -> None:
    assert _unknown.declared_ports(ENTRIES) == frozenset({9, 8140, 443, 80})


def test_parse_prefers_cmdline_and_dedupes(sysroot: Path) -> None:
    _proc(sysroot, 4243, b".venv/bin/python\x00-m\x00issue_dashboard\x00")
    _proc(sysroot, 4242, b"")
    found = _unknown.parse_listeners(SS)
    by_key = {(item.address, item.port): item.process for item in found}
    assert by_key["127.0.0.1", 8798] == ".venv/bin/python -m issue_dashboard"
    assert by_key["127.0.0.1", 8140] == "python"
    assert by_key[ANY, 22] == ""
    assert ("*", 80) not in by_key


def test_a_repeated_socket_is_listed_once() -> None:
    line = 'LISTEN 0 5 127.0.0.1:8141 0.0.0.0:* users:(("python",pid=7747,fd=3))'
    found = _unknown.parse_listeners(f"{line}\n{line}\n")
    assert [(item.address, item.port) for item in found] == [("127.0.0.1", 8141)]


def test_unknown_filters_declared_ignored_own_and_noise(sysroot: Path) -> None:
    del sysroot
    runner = FakeRunner({_unknown.SS_ARGV: ok(_unknown.SS_ARGV, SS)})
    ignored = (IgnoredListener(port=22, why="sshd"),)
    found = _unknown.unknown_listeners(runner, ENTRIES, ignored, own_port=8760)
    assert [(item.address, item.port) for item in found] == [
        ("127.0.0.1", 8798),
        ("[::1]", 8798),
        (ANY, 52736),
    ]


def test_unknown_is_empty_when_ss_fails() -> None:
    assert _unknown.unknown_listeners(FakeRunner({}), ENTRIES, (), 1) == []


def test_ephemeral_floor_reads_the_kernel_range(sysroot: Path) -> None:
    assert _unknown.ephemeral_floor() == _unknown.DEFAULT_EPHEMERAL_FLOOR
    path = sysroot / _unknown.PORT_RANGE.lstrip("/")
    path.parent.mkdir(parents=True)
    path.write_text("40000\t60999\n")
    assert _unknown.ephemeral_floor() == 40000
    path.write_text("junk\n")
    assert _unknown.ephemeral_floor() == _unknown.DEFAULT_EPHEMERAL_FLOOR
    path.write_text("")
    assert _unknown.ephemeral_floor() == _unknown.DEFAULT_EPHEMERAL_FLOOR


def test_noise_is_loopback_and_ephemeral_only() -> None:
    assert _unknown._is_noise(Listener("127.0.0.1", 40000), 32768)
    assert not _unknown._is_noise(Listener(ANY, 40000), 32768)
    assert not _unknown._is_noise(Listener("127.0.0.1", 8000), 32768)


def test_undeclared_units(sysroot: Path) -> None:
    directory = sysroot / "home/tester" / _unknown.USER_UNIT_DIR
    assert _unknown.undeclared_units(ENTRIES) == []
    (directory / "default.target.wants").mkdir(parents=True)
    for name in ("declared.service", "stray.timer", "notes.txt", "sys.service"):
        (directory / name).write_text("[Unit]\n")
    (directory / "vendor.service").symlink_to(
        "/usr/lib/systemd/user/dbus-broker.service"
    )
    (directory / "dangling.service").symlink_to(directory / "nowhere")
    names = [item.name for item in _unknown.undeclared_units(ENTRIES)]
    assert names == ["stray.timer", "sys.service"]


def test_own_symlink_counts(sysroot: Path) -> None:
    directory = sysroot / "home/tester" / _unknown.USER_UNIT_DIR
    directory.mkdir(parents=True)
    (sysroot / "real.service").write_text("[Unit]\n")
    (directory / "linked.service").symlink_to(sysroot / "real.service")
    assert [u.name for u in _unknown.undeclared_units(ENTRIES)] == ["linked.service"]
