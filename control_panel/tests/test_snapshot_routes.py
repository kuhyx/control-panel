"""Routes read through the snapshot cache: mutations and logs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from control_panel import _manifest, _routes, _snapshot
from control_panel._manifest import ManifestLog
from control_panel.mutations import _restart, _types
from control_panel.tests import _fixture_fleet as fleet

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_T0 = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)


class Ticking:
    """A clock that moves one second per reading."""

    def __init__(self) -> None:
        self.now = _T0

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


def _router(state: dict[str, str]) -> _routes.Router:
    cache = _snapshot.SnapshotCache(
        lambda: {"subsystems": [{"id": "alpha", "state": state["now"]}]},
        clock=Ticking(),
    )
    return _routes.Router(object(), 8770, snapshot=cache)


def test_a_mutation_is_visible_in_the_very_next_get(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"now": "ACTIVE"}

    def restart(_runner: object, _body: object) -> _types.MutationResult:
        state["now"] = "RESTARTED"
        return _types.MutationResult.success("restarted")

    monkeypatch.setattr(_restart, "apply", restart)
    made = _router(state)
    _, before = made.resolve("/api/status/alpha")
    assert before["state"] == "ACTIVE"
    made.mutate("restart", {"kind": "unit", "name": "a.service"})
    _, after = made.resolve("/api/status/alpha")
    assert after["state"] == "RESTARTED"


def test_a_cold_mutation_does_not_collect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _restart, "apply", lambda _r, _b: _types.MutationResult.success("ok")
    )
    made = _router({"now": "ACTIVE"})
    made.mutate("restart", {})
    assert made.snapshot.generation == 0


def test_logs_are_served_without_any_snapshot(
    monkeypatch: pytest.MonkeyPatch, sysroot: Path
) -> None:
    log = sysroot / "var/log/a.log"
    log.parent.mkdir(parents=True)
    log.write_text("one\n")
    declared = ManifestLog(id="a-log", kind="file", path="/var/log/a.log")
    monkeypatch.setattr(
        _manifest, "load_manifest", lambda: (fleet.entry(logs=(declared,)),)
    )

    def never() -> dict[str, Any]:
        message = "a log read must not collect the fleet"
        raise AssertionError(message)

    made = _routes.Router(object(), 8770, snapshot=_snapshot.SnapshotCache(never))
    status, payload = made.resolve("/api/logs/a-log")
    assert status is HTTPStatus.OK
    assert payload["lines"] == ("one",)
