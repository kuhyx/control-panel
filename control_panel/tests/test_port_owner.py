"""Port-clash detection: a declared dashboard's port held by a foreign owner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from control_panel import _port_owner
from control_panel._manifest_live import ManifestContainer, ManifestDashboard
from control_panel._types import Scope
from control_panel.tests import _fixture_fleet as fleet

if TYPE_CHECKING:
    from pathlib import Path

    from control_panel._manifest import ManifestEntry

GITEA_ID = "c22c7199215b9b1573a2313b12f13dd3875b1c847cb855713157a088356397a8"
USER_APP = "0::/user.slice/user-1000.slice/user@1000.service/app.slice"

# Real `ss -ltnpH` lines from the machine this was found on.
SS = (
    "LISTEN 0 1024 127.0.0.1:8780 0.0.0.0:* "
    'users:(("python3",pid=1735,fd=11))\n'
    "LISTEN 0 4096 127.0.0.1:8089 0.0.0.0:*\n"
    "LISTEN 0 4096 *:8088 *:*\n"
    "LISTEN 0 2048 127.0.0.1:8141 0.0.0.0:* "
    'users:(("python",pid=7747,fd=7),("python",pid=7747,fd=3))\n'
    "LISTEN 0 4096 127.0.0.1:3000 0.0.0.0:* "
    'users:(("gitea",pid=4321,fd=14))\n'
    "LISTEN 0 5 100.109.64.41:5600 0.0.0.0:* "
    'users:(("python3",pid=9229,fd=6))\n'
    "LISTEN 0 32 127.0.0.1%lo:53 0.0.0.0:*\n"
    "short line\n"
    "LISTEN 0 5 [::1]:notaport [::]:*\n"
)

PROC = {
    1735: (
        f"{USER_APP}/anki-syncserver.service",
        "/usr/bin/python3 -m anki.syncserver",
    ),
    7747: (f"{USER_APP}/popes-site.service", "python -m signal_bot.popes_site"),
    4321: (f"0::/system.slice/docker-{GITEA_ID}.scope", "/usr/local/bin/gitea web"),
    1365111: ("0::/user.slice/user-1000.slice/session-253.scope", "book-guard-desktop"),
    1000: ("0::/system.slice/dufs.service", "/usr/local/bin/dufs"),
}


def _reader(pid: int, name: str) -> str | None:
    """Fake /proc: cgroup and cmdline for the pids above, None for the rest."""
    if pid not in PROC:
        return None
    cgroup, cmdline = PROC[pid]
    return cgroup if name == "cgroup" else cmdline


def _entry(
    url: str,
    units: tuple[tuple[str, Scope], ...] = (),
    containers: tuple[str, ...] = (),
) -> ManifestEntry:
    return fleet.live_entry(
        dashboards=(ManifestDashboard(label="UI", url=url, on_demand=True),),
        containers=tuple(ManifestContainer(name=c) for c in containers),
        units=tuple(fleet.service(name, scope) for name, scope in units),
    )


def _clash(entry: ManifestEntry, ss: str = SS) -> str | None:
    resolve = _port_owner.OwnerResolver({"gitea": GITEA_ID[:12]}, _reader)
    url = entry.live.dashboards[0].url
    return _port_owner.clash(entry, url, _port_owner.parse_listeners(ss), resolve)


def test_parse_listeners_keeps_every_pid_once_and_strips_interface() -> None:
    found = _port_owner.parse_listeners(SS)
    assert found[8141] == [("127.0.0.1", (7747,))]
    assert found[8089] == [("127.0.0.1", ())]
    assert found[53] == [("127.0.0.1", ())]
    assert 0 not in found


def test_foreign_unit_on_the_port_is_a_clash_naming_the_owner() -> None:
    entry = _entry(
        "http://127.0.0.1:8780/",
        units=(("mangatl.service", Scope.USER), ("mangatl-llm.service", Scope.USER)),
    )
    assert _clash(entry) == (
        "port 8780 held by anki-syncserver.service "
        "(pid 1735 /usr/bin/python3 -m anki.syncserver)"
    )


def test_own_user_unit_is_not_a_clash() -> None:
    entry = _entry(
        "http://127.0.0.1:8141/", units=(("popes-site.service", Scope.USER),)
    )
    assert _clash(entry) is None


def test_same_unit_name_in_the_other_scope_is_foreign() -> None:
    entry = _entry(
        "http://127.0.0.1:8141/", units=(("popes-site.service", Scope.SYSTEM),)
    )
    assert _clash(entry) is not None


def test_own_system_unit_is_not_a_clash() -> None:
    ss = 'LISTEN 0 1 127.0.0.1:5000 0.0.0.0:* users:(("dufs",pid=1000,fd=9))'
    entry = _entry("http://127.0.0.1:5000/", units=(("dufs.service", Scope.SYSTEM),))
    assert _clash(entry, ss) is None


def test_own_container_is_matched_by_short_id_prefix() -> None:
    assert _clash(_entry("http://127.0.0.1:3000/", containers=("gitea",))) is None


def test_another_subsystems_container_is_a_clash() -> None:
    clash = _clash(_entry("http://127.0.0.1:3000/", containers=("other",)))
    assert (
        clash == "port 3000 held by container gitea (pid 4321 /usr/local/bin/gitea web)"
    )


@pytest.mark.parametrize(
    "url",
    [
        # docker-proxy is root's: ss names no process, so no verdict.
        "http://127.0.0.1:8089/",
        "http://127.0.0.1:8088/",
        # nothing listening at all.
        "http://127.0.0.1:9999/",
        # not loopback: a tailnet address and a public URL are never judged.
        "http://100.109.64.41:5600/",
        "https://dice.kuhy.duckdns.org/",
        "http://127.0.0.1:bad/",
    ],
)
def test_invisible_absent_or_non_loopback_owner_is_never_a_clash(url: str) -> None:
    assert _clash(_entry(url, units=(("x.service", Scope.USER),))) is None


def test_hand_started_session_process_is_unattributable() -> None:
    ss = 'LISTEN 0 1 127.0.0.1:8773 0.0.0.0:* users:(("dart",pid=1365111,fd=7))'
    entry = _entry("http://127.0.0.1:8773/", units=(("book-guard.timer", Scope.USER),))
    assert _clash(entry, ss) is None


def test_vanished_pid_is_unattributable() -> None:
    ss = 'LISTEN 0 1 127.0.0.1:8780 0.0.0.0:* users:(("python3",pid=42,fd=3))'
    assert _clash(_entry("http://127.0.0.1:8780/"), ss) is None


def test_ipv6_only_listener_does_not_serve_an_ipv4_dashboard() -> None:
    ss = 'LISTEN 0 1 [::1]:8780 [::]:* users:(("python3",pid=1735,fd=3))'
    assert _clash(_entry("http://127.0.0.1:8780/"), ss) is None
    assert _clash(_entry("http://localhost:8780/"), ss) is not None


def test_default_ports_come_from_the_scheme() -> None:
    ss = 'LISTEN 0 1 0.0.0.0:80 0.0.0.0:* users:(("x",pid=1735,fd=3))'
    assert _clash(_entry("http://127.0.0.1/"), ss) is not None
    ss443 = ss.replace(":80 ", ":443 ")
    assert _clash(_entry("https://127.0.0.1/"), ss443) is not None


@pytest.mark.parametrize(
    ("cgroup", "expected"),
    [
        (f"{USER_APP}/a.service", ("unit", "a.service", Scope.USER)),
        (f"{USER_APP}/a.service/payload", ("unit", "a.service", Scope.USER)),
        ("0::/system.slice/b.service", ("unit", "b.service", Scope.SYSTEM)),
        (f"0::/system.slice/docker-{GITEA_ID}.scope", ("container", GITEA_ID, None)),
        (f"0::/docker/{GITEA_ID}", ("container", GITEA_ID, None)),
        ("0::/user.slice/user-1000.slice/session-2.scope", None),
        (f"{USER_APP}/app-firefox-1.scope", None),
        ("0::/user.slice/user-1000.slice/user@1000.service/init.scope", None),
        ("0::/user.slice/user-1000.slice/user@1000.service", None),
        ("0::/user.slice", None),
        ("0::/", None),
        ("1:name=systemd:/foo.service", None),
        ("", None),
    ],
)
def test_attribute(cgroup: str, expected: tuple[str, str, Scope | None] | None) -> None:
    assert _port_owner.attribute(cgroup) == expected


def test_container_scope_with_unknown_id_is_unattributable() -> None:
    resolve = _port_owner.OwnerResolver({"gitea": "ffffffffffff"}, _reader)
    assert resolve(4321) is None


def test_resolver_reads_each_pid_once() -> None:
    calls: list[tuple[int, str]] = []

    def reader(pid: int, name: str) -> str | None:
        calls.append((pid, name))
        return _reader(pid, name)

    resolve = _port_owner.OwnerResolver({}, reader)
    first = resolve(1735)
    assert resolve(1735) is first
    assert calls == [(1735, "cgroup"), (1735, "cmdline")]


def test_owner_without_cmdline_describes_unit_and_pid() -> None:
    owner = _port_owner.Owner(kind="unit", name="a.service", pid=7)
    assert owner.describe() == "a.service (pid 7)"


def test_read_proc_reads_under_the_sysroot(sysroot: Path) -> None:
    (sysroot / "proc/5").mkdir(parents=True)
    (sysroot / "proc/5/cmdline").write_bytes(b"python3\x00-m\x00x\x00")
    assert _port_owner.read_proc(5, "cmdline") == "python3 -m x"
    assert _port_owner.read_proc(6, "cmdline") is None


def test_listening_reports_none_off_loopback() -> None:
    listeners = _port_owner.parse_listeners(SS)
    assert _port_owner.listening("http://127.0.0.1:8089/", listeners) is True
    assert _port_owner.listening("http://127.0.0.1:8781/", listeners) is False
    assert _port_owner.listening("https://kuhy.duckdns.org/", listeners) is None
