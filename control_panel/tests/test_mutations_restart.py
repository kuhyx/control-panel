from __future__ import annotations

import pytest

from control_panel import _manifest
from control_panel._manifest_live import ManifestContainer
from control_panel._runner import CommandResult
from control_panel._types import Category
from control_panel.mutations import _restart
from control_panel.tests import _fixture_fleet as fleet
from control_panel.tests._fixture_runner import FakeRunner, ok

USER_RESTART = ("systemctl", "--user", "restart", "bot.service")
DOCKER_RESTART = ("docker", "restart", "gitea")


@pytest.fixture(autouse=True)
def manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    """A server with restartable members, and a guard beside it."""
    server = fleet.live_entry(
        id="srv",
        category=Category.SERVER,
        units=(
            fleet.service("bot.service", restartable=True),
            fleet.service("plain.service"),
        ),
        containers=(
            ManifestContainer(name="gitea", restartable=True),
            ManifestContainer(name="db"),
        ),
    )
    guard = fleet.live_entry(
        id="guard", units=(fleet.service("workout-locker.service"),)
    )
    monkeypatch.setattr(_manifest, "load_manifest", lambda: (server, guard))


@pytest.mark.parametrize(
    "body",
    [None, [], {"kind": "unit"}, {"kind": "stop", "name": "bot.service"}],
)
def test_malformed_requests_fail(body: object) -> None:
    runner = FakeRunner({})
    result = _restart.apply(runner, body)
    assert not result.ok
    assert not result.refused
    assert runner.calls == []


@pytest.mark.parametrize(
    ("kind", "name"),
    [
        ("unit", "workout-locker.service"),
        ("unit", "plain.service"),
        ("container", "db"),
        ("container", "bot.service"),
        ("unit", "gitea"),
    ],
)
def test_anything_not_allowlisted_is_refused(kind: str, name: str) -> None:
    runner = FakeRunner({})
    result = _restart.apply(runner, {"kind": kind, "name": name})
    assert result.refused
    assert "not restartable" in result.summary
    assert runner.calls == []


def test_user_unit_restart() -> None:
    runner = FakeRunner({USER_RESTART: ok(USER_RESTART, "")})
    result = _restart.apply(runner, {"kind": "unit", "name": "bot.service"})
    assert result.ok
    assert result.argv == USER_RESTART


def test_container_restart() -> None:
    runner = FakeRunner({DOCKER_RESTART: ok(DOCKER_RESTART, "gitea\n")})
    result = _restart.apply(runner, {"kind": "container", "name": "gitea"})
    assert result.ok
    assert runner.calls == [DOCKER_RESTART]


def test_failed_restart_relays_the_error() -> None:
    failed = CommandResult(
        argv=USER_RESTART, returncode=1, stdout="", stderr=" Job failed \n"
    )
    result = _restart.apply(
        FakeRunner({USER_RESTART: failed}), {"kind": "unit", "name": "bot.service"}
    )
    assert not result.ok
    assert result.stderr == "Job failed"
