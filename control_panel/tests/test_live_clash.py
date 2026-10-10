"""Port clashes and stopped on-demand dashboards in the live collection."""

from typing import TYPE_CHECKING

import pytest

from control_panel import _docker, _live, _unknown
from control_panel._live_types import DashboardRecord, ProbeRecord
from control_panel._manifest_live import ManifestContainer, ManifestDashboard
from control_panel._types import Arming, Category, Scope, UnitRecord, UnitState
from control_panel.tests import _fixture_fleet as fleet
from control_panel.tests._fixture_runner import FakeRunner, ok

if TYPE_CHECKING:
    from pathlib import Path

    from control_panel._manifest import ManifestEntry

UP = ProbeRecord(kind="http", target="u", up=True, status=200)
DOWN = ProbeRecord(kind="tcp", target="127.0.0.1:1", up=False)
PUBLIC = ProbeRecord(kind="http", target="https://x/", up=None)
CLASH = "port 8780 held by anki-syncserver.service (pid 1735)"
APP_SLICE = "user.slice/user-1000.slice/user@1000.service/app.slice"


def test_clash_is_dead_even_when_the_probe_answers() -> None:
    clashing = DashboardRecord(label="UI", url="u", probe=UP, clash=CLASH)
    view = _live.LiveView(dashboards=(clashing,))
    assert _live.states(Category.SERVER, view) == (Arming.ARMED, Arming.BAD)
    assert _live.states(Category.ENFORCEMENT, view) == (
        Arming.ARMED,
        Arming.DEGRADED,
    )
    assert _live.reason(view) == f"port clash: UI: {CLASH}"


def test_reason_joins_down_and_clash() -> None:
    view = _live.LiveView(
        probes=(DOWN,),
        dashboards=(DashboardRecord(label="UI", url="u", probe=PUBLIC, clash=CLASH),),
    )
    assert _live.reason(view) == f"down: 127.0.0.1:1; port clash: UI: {CLASH}"


def _proc(sysroot: Path, pid: int, cgroup: str, cmdline: bytes) -> None:
    (sysroot / f"proc/{pid}").mkdir(parents=True)
    (sysroot / f"proc/{pid}/cgroup").write_text(f"0::/{cgroup}\n")
    (sysroot / f"proc/{pid}/cmdline").write_bytes(cmdline)


def _record(name: str, active: str | None) -> UnitRecord:
    return UnitRecord(
        name=name,
        scope=Scope.USER,
        arming=Arming.ARMED,
        state=UnitState(active_state=active),
    )


def _mangatl(url: str = "http://127.0.0.1:8780/") -> ManifestEntry:
    return fleet.live_entry(
        category=Category.SERVER,
        units=(
            fleet.service("mangatl.service", on_demand=True),
            fleet.service("mangatl-llm.service", on_demand=True),
            fleet.timer("unrelated.timer"),
        ),
        dashboards=(ManifestDashboard(label="mangatl", url=url, on_demand=True),),
    )


def _ss(stdout: str) -> FakeRunner:
    return FakeRunner({_unknown.SS_ARGV: ok(_unknown.SS_ARGV, stdout)})


ANKI_SS = 'LISTEN 0 1 127.0.0.1:8780 0.0.0.0:* users:(("python3",pid=1735,fd=11))'
INACTIVE = (
    _record("mangatl.service", "inactive"),
    _record("mangatl-llm.service", "failed"),
    _record("unrelated.timer", "active"),
)


@pytest.mark.usefixtures("fake_probes")
def test_collect_flags_a_foreign_owner_and_reports_stopped(sysroot: Path) -> None:
    _proc(
        sysroot,
        1735,
        f"{APP_SLICE}/anki-syncserver.service",
        b"/usr/bin/python3\x00-m\x00anki.syncserver\x00",
    )
    runner = _ss(ANKI_SS)
    entry = _mangatl()
    dashboard = _live.collect(runner, (entry,), {"s": INACTIVE})["s"].dashboards[0]
    assert runner.calls == [_unknown.SS_ARGV]
    assert dashboard.clash == (
        "port 8780 held by anki-syncserver.service "
        "(pid 1735 /usr/bin/python3 -m anki.syncserver)"
    )
    # A foreign owner does not make mangatl itself running.
    assert dashboard.stopped is True


@pytest.mark.usefixtures("fake_probes")
def test_on_demand_dashboard_with_inactive_units_and_free_port_is_stopped() -> None:
    entry = _mangatl("http://127.0.0.1:8781/")
    view = _live.collect(_ss(ANKI_SS), (entry,), {"s": INACTIVE})["s"]
    assert view.dashboards[0].stopped is True
    assert view.dashboards[0].clash is None


@pytest.mark.usefixtures("fake_probes")
@pytest.mark.parametrize(
    "records",
    [
        (
            _record("mangatl.service", "active"),
            _record("mangatl-llm.service", "active"),
        ),
        (
            _record("mangatl.service", "inactive"),
            _record("mangatl-llm.service", "activating"),
        ),
        # Unread ActiveState is not evidence of "stopped".
        (_record("mangatl.service", None), _record("mangatl-llm.service", None)),
        (),
    ],
)
def test_running_or_unknown_units_are_not_stopped(
    records: tuple[UnitRecord, ...],
) -> None:
    entry = _mangatl("http://127.0.0.1:8781/")
    dashboard = _live.collect(_ss(""), (entry,), {"s": records})["s"].dashboards[0]
    assert dashboard.stopped is False


@pytest.mark.usefixtures("fake_probes")
def test_hand_started_server_on_the_port_is_not_stopped(sysroot: Path) -> None:
    _proc(sysroot, 77, "user.slice/user-1000.slice/session-2.scope", b"mangatl\x00")
    ss = 'LISTEN 0 1 127.0.0.1:8781 0.0.0.0:* users:(("mangatl",pid=77,fd=3))'
    entry = _mangatl("http://127.0.0.1:8781/")
    dashboard = _live.collect(_ss(ss), (entry,), {"s": INACTIVE})["s"].dashboards[0]
    assert dashboard.stopped is False
    assert dashboard.clash is None


@pytest.mark.usefixtures("fake_probes")
def test_without_unit_records_nothing_is_stopped() -> None:
    entry = _mangatl("http://127.0.0.1:8781/")
    assert _live.collect(_ss(""), (entry,))["s"].dashboards[0].stopped is False


@pytest.mark.usefixtures("fake_probes")
def test_timers_only_subsystem_is_judged_on_all_its_units() -> None:
    entry = fleet.live_entry(
        units=(fleet.timer("book-guard.timer"),),
        dashboards=(
            ManifestDashboard(
                label="App", url="http://127.0.0.1:8773/", on_demand=True
            ),
        ),
    )
    active = {"s": (_record("book-guard.timer", "active"),)}
    resting = {"s": (_record("book-guard.timer", "inactive"),)}
    assert _live.collect(_ss(""), (entry,), active)["s"].dashboards[0].stopped is False
    assert _live.collect(_ss(""), (entry,), resting)["s"].dashboards[0].stopped is True


@pytest.mark.usefixtures("fake_probes")
def test_ss_is_skipped_without_loopback_dashboards_and_failure_is_empty() -> None:
    public = fleet.live_entry(
        dashboards=(ManifestDashboard(label="Pub", url="https://x.example/"),)
    )
    runner = FakeRunner({})
    _live.collect(runner, (public,))
    assert runner.calls == []
    failing = FakeRunner({})
    view = _live.collect(failing, (_mangatl(),), {"s": INACTIVE})["s"]
    assert failing.calls == [_unknown.SS_ARGV]
    assert view.dashboards[0].clash is None


@pytest.mark.usefixtures("fake_probes")
def test_docker_ids_let_a_declared_container_own_its_port(sysroot: Path) -> None:
    cid = "c22c7199215b" + "0" * 52
    _proc(sysroot, 4321, f"system.slice/docker-{cid}.scope", b"gitea\x00web\x00")
    ss = 'LISTEN 0 1 127.0.0.1:3000 0.0.0.0:* users:(("gitea",pid=4321,fd=14))'
    ps = "gitea\trunning\tUp 4 days\tc22c7199215b"
    runner = FakeRunner(
        {
            _unknown.SS_ARGV: ok(_unknown.SS_ARGV, ss),
            _docker.PS_ARGV: ok(_docker.PS_ARGV, ps),
        }
    )
    dashboards = (ManifestDashboard(label="UI", url="http://127.0.0.1:3000/"),)
    own = fleet.live_entry(
        dashboards=dashboards, containers=(ManifestContainer(name="gitea"),)
    )
    other = fleet.live_entry(
        id="o", dashboards=dashboards, containers=(ManifestContainer(name="x"),)
    )
    views = _live.collect(runner, (own, other))
    assert views["s"].dashboards[0].clash is None
    assert views["o"].dashboards[0].clash == (
        "port 3000 held by container gitea (pid 4321 gitea web)"
    )
