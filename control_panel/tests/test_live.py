from __future__ import annotations

from control_panel import _docker, _live
from control_panel._live_types import ContainerRecord, DashboardRecord, ProbeRecord
from control_panel._manifest import ManifestProbe
from control_panel._manifest_live import ManifestContainer, ManifestDashboard
from control_panel._types import Arming, Category
from control_panel.tests import _fixture_fleet as fleet
from control_panel.tests._fixture_runner import FakeRunner, ok

UP = ProbeRecord(kind="http", target="u", up=True, status=200)
DOWN = ProbeRecord(kind="tcp", target="127.0.0.1:1", up=False)
PUBLIC = ProbeRecord(kind="http", target="https://x/", up=None)


def test_collect_probes_dashboards_but_skips_on_demand(
    fake_probes: list[tuple[str, str]],
) -> None:
    entry = fleet.live_entry(
        probes=(ManifestProbe(kind="tcp", target="127.0.0.1:9"),),
        dashboards=(
            ManifestDashboard(label="UI", url="http://127.0.0.1:8/"),
            ManifestDashboard(label="App", url="http://127.0.0.1:7/", on_demand=True),
        ),
        containers=(ManifestContainer(name="c"),),
    )
    argv = _docker.PS_ARGV
    views = _live.collect(FakeRunner({argv: ok(argv, "c\trunning\tUp")}), (entry,))
    view = views["s"]
    assert ("http", "http://127.0.0.1:7/") not in fake_probes
    assert view.dashboards[0].probe.up is True
    assert view.dashboards[1].probe.up is None
    assert view.probes[0].target == "127.0.0.1:9"
    assert view.containers[0].arming is Arming.ARMED


def test_collect_skips_docker_when_nothing_declares_a_container(
    fake_probes: list[tuple[str, str]],
) -> None:
    runner = FakeRunner({})
    views = _live.collect(runner, (fleet.live_entry(),))
    assert views["s"] == _live.LiveView()
    assert runner.calls == []
    assert fake_probes == []


def test_dead_probe_is_bad_on_a_server_and_degraded_elsewhere() -> None:
    view = _live.LiveView(probes=(DOWN, PUBLIC))
    assert _live.states(Category.SERVER, view) == (Arming.BAD,)
    assert _live.states(Category.ENFORCEMENT, view) == (Arming.DEGRADED,)


def test_states_include_dashboards_and_containers() -> None:
    view = _live.LiveView(
        dashboards=(DashboardRecord(label="UI", url="u", probe=UP),),
        containers=(ContainerRecord(name="c", arming=Arming.DEGRADED),),
    )
    assert _live.states(Category.SERVER, view) == (Arming.ARMED, Arming.DEGRADED)


def test_reason_names_everything_down() -> None:
    view = _live.LiveView(
        probes=(DOWN, UP),
        dashboards=(
            DashboardRecord(label="UI", url="u", probe=DOWN),
            DashboardRecord(label="Fine", url="v", probe=UP),
        ),
        containers=(
            ContainerRecord(name="c", arming=Arming.BAD, state="exited"),
            ContainerRecord(
                name="d", arming=Arming.UNKNOWN, status="docker unavailable"
            ),
            ContainerRecord(name="e", arming=Arming.ARMED, state="running"),
        ),
    )
    assert _live.reason(view) == (
        "down: 127.0.0.1:1, UI, c (exited), d (docker unavailable)"
    )
    assert _live.reason(_live.LiveView()) == ""
