from __future__ import annotations

import pytest

from control_panel import _docker
from control_panel._manifest_live import ManifestContainer
from control_panel._types import Arming
from control_panel.tests import _fixture_fleet as fleet
from control_panel.tests._fixture_runner import FakeRunner, ok

PS = (
    "gitea\trunning\tUp 4 days\n"
    "signal-api\trunning\tUp 4 days (unhealthy)\n"
    "old\texited\tExited (1) 2 days ago\n"
    "garbage line"
)


def test_list_containers_parses_tab_rows() -> None:
    runner = FakeRunner({_docker.PS_ARGV: ok(_docker.PS_ARGV, PS)})
    rows = _docker.list_containers(runner)
    assert rows == {
        "gitea": ("running", "Up 4 days"),
        "signal-api": ("running", "Up 4 days (unhealthy)"),
        "old": ("exited", "Exited (1) 2 days ago"),
    }


def test_list_containers_none_when_docker_fails() -> None:
    assert _docker.list_containers(FakeRunner({})) is None
    assert _docker.read_containers(FakeRunner({})) is None


def test_read_containers_maps_names_to_short_ids() -> None:
    stdout = "gitea\trunning\tUp 4 days\tc22c7199215b\nold\texited\tExited (1)"
    runner = FakeRunner({_docker.PS_ARGV: ok(_docker.PS_ARGV, stdout)})
    assert _docker.read_containers(runner) == (
        {"gitea": ("running", "Up 4 days"), "old": ("exited", "Exited (1)")},
        {"gitea": "c22c7199215b"},
    )


@pytest.mark.parametrize(
    ("state", "status", "expected"),
    [
        ("running", "Up", Arming.ARMED),
        ("running", "Up (unhealthy)", Arming.DEGRADED),
        ("restarting", "Restarting", Arming.DEGRADED),
        ("exited", "Exited (0)", Arming.BAD),
        ("weird", "", Arming.UNKNOWN),
    ],
)
def test_arming_mapping(state: str, status: str, expected: Arming) -> None:
    assert _docker._arming(state, status) is expected


def test_collect_covers_present_missing_and_unavailable() -> None:
    entry = fleet.live_entry(
        containers=(
            ManifestContainer(name="gitea", restartable=True),
            ManifestContainer(name="gone"),
        )
    )
    found = _docker.collect((entry,), {"gitea": ("running", "Up")})["s"]
    assert [(c.name, c.arming, c.restartable) for c in found] == [
        ("gitea", Arming.ARMED, True),
        ("gone", Arming.NOT_INSTALLED, False),
    ]
    unknown = _docker.collect((entry,), None)["s"]
    assert {c.arming for c in unknown} == {Arming.UNKNOWN}
    assert unknown[0].status == "docker unavailable"
