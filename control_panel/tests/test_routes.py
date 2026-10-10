from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

from control_panel import _manifest, _routes
from control_panel._manifest import ManifestLog
from control_panel.tests import _fixture_fleet as fleet

if TYPE_CHECKING:
    from pathlib import Path

STATUS: dict[str, Any] = {
    "subsystems": [
        {
            "id": "alpha",
            "logs": [
                {"id": "a-log", "kind": "file", "path": "/var/log/a.log", "unit": None},
                {
                    "id": "ajournal",
                    "kind": "journal",
                    "path": None,
                    "unit": "a.service",
                    "scope": "user",
                },
            ],
        }
    ]
}


# Log specs are looked up in the manifest, not the snapshot.
LOG_ENTRY = fleet.entry(
    logs=(ManifestLog(id="a-log", kind="file", path="/var/log/a.log"),)
)


@pytest.fixture
def router(monkeypatch: pytest.MonkeyPatch) -> _routes.Router:
    made = _routes.Router.__new__(_routes.Router)
    monkeypatch.setattr(_routes.Router, "_status", lambda _self: STATUS)
    monkeypatch.setattr(_manifest, "load_manifest", lambda: (LOG_ENTRY,))
    made._port = 8770
    return made


def test_non_api_paths_are_not_ours(router: _routes.Router) -> None:
    assert router.resolve("/index.html") is None
    assert router.resolve("/") is None


def test_health(router: _routes.Router) -> None:
    status, payload = router.resolve("/api/health")
    assert status is HTTPStatus.OK
    assert payload == {"ok": True, "port": 8770}


def test_unknown_endpoint_is_404(router: _routes.Router) -> None:
    status, payload = router.resolve("/api/nope")
    assert status is HTTPStatus.NOT_FOUND
    assert "no such endpoint" in payload["error"]


def test_whole_fleet_status(router: _routes.Router) -> None:
    status, payload = router.resolve("/api/status")
    assert status is HTTPStatus.OK
    assert payload["subsystems"][0]["id"] == "alpha"


def test_single_subsystem(router: _routes.Router) -> None:
    status, payload = router.resolve("/api/status/alpha")
    assert status is HTTPStatus.OK
    assert payload["id"] == "alpha"


def test_unknown_subsystem_is_404(router: _routes.Router) -> None:
    status, payload = router.resolve("/api/status/ghost")
    assert status is HTTPStatus.NOT_FOUND
    assert "ghost" in payload["error"]


def test_log_tail(router: _routes.Router, sysroot: Path) -> None:
    log = sysroot / "var/log/a.log"
    log.parent.mkdir(parents=True)
    log.write_text("one\ntwo\nthree\n")
    status, payload = router.resolve("/api/logs/a-log?lines=2")
    assert status is HTTPStatus.OK
    # asdict keeps tuples; json.dumps renders them as arrays on the wire.
    assert payload["lines"] == ("two", "three")
    assert payload["path"] == "/var/log/a.log"


def test_missing_log_id_is_404(router: _routes.Router) -> None:
    status, _ = router.resolve("/api/logs/")
    assert status is HTTPStatus.NOT_FOUND


def test_unknown_log_is_404(router: _routes.Router) -> None:
    status, payload = router.resolve("/api/logs/ghost")
    assert status is HTTPStatus.NOT_FOUND
    assert "ghost" in payload["error"]


@pytest.mark.parametrize(
    ("query", "expected"), [("", 200), ("lines=7", 7), ("lines=abc", 200)]
)
def test_line_parameter_parsing(query: str, expected: int) -> None:
    assert _routes._int_param(query, "lines", 200) == expected


def test_router_uses_the_runner_and_port_it_was_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[object, int]] = []

    def record(runner: object, port: int) -> object:
        seen.append((runner, port))
        return _FAKE_STATUS

    monkeypatch.setattr(_routes._aggregate, "build_status", record)
    monkeypatch.setattr(_routes, "to_payload", lambda status: {"subsystems": []})
    sentinel = object()
    made = _routes.Router(sentinel, 1234)
    made.resolve("/api/status")
    assert seen == [(sentinel, 1234)]


_FAKE_STATUS = object()


def test_why_route_serves_rationale(monkeypatch: pytest.MonkeyPatch) -> None:
    from control_panel import _manifest, _rationale
    from control_panel.tests import _fixture_fleet as fleet

    monkeypatch.setattr(_manifest, "load_manifest", lambda: (fleet.entry(),))
    monkeypatch.setattr(
        _rationale,
        "build",
        lambda _runner, entry: _rationale.Rationale(subsystem=entry.id),
    )
    made = _routes.Router(object(), 8770)
    status, payload = made.resolve("/api/why/s")
    assert status is HTTPStatus.OK
    assert payload["subsystem"] == "s"


def test_why_route_404s_for_an_unknown_subsystem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from control_panel import _manifest
    from control_panel.tests import _fixture_fleet as fleet

    monkeypatch.setattr(_manifest, "load_manifest", lambda: (fleet.entry(),))
    made = _routes.Router(object(), 8770)
    status, payload = made.resolve("/api/why/ghost")
    assert status is HTTPStatus.NOT_FOUND
    assert "ghost" in payload["error"]


def test_mutate_dispatches_to_the_named_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from control_panel.mutations import _shutdown_hours, _types

    monkeypatch.setattr(
        _shutdown_hours,
        "apply",
        lambda _runner, _body: _types.MutationResult.success("done"),
    )
    made = _routes.Router(object(), 8770)
    status, payload = made.mutate("shutdown-hours", {})
    assert status is HTTPStatus.OK
    assert payload["ok"] is True


def test_a_refusal_is_a_200_carrying_the_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from control_panel.mutations import _shutdown_hours, _types

    monkeypatch.setattr(
        _shutdown_hours,
        "apply",
        lambda _runner, _body: _types.MutationResult.refusal("no", "not stricter"),
    )
    made = _routes.Router(object(), 8770)
    # Not a 4xx: the guard working is not the dashboard being broken.
    status, payload = made.mutate("shutdown-hours", {})
    assert status is HTTPStatus.OK
    assert payload["refused"] is True
    assert payload["stderr"] == "not stricter"


def test_an_unknown_mutation_is_404() -> None:
    made = _routes.Router(object(), 8770)
    status, payload = made.mutate("rm-rf", {})
    assert status is HTTPStatus.NOT_FOUND
    assert "rm-rf" in payload["error"]


def test_steam_exceptions_are_readable_over_get(sysroot: object) -> None:
    made = _routes.Router(object(), 8770)
    status, payload = made.resolve("/api/mutate/steam-exceptions")
    assert status is HTTPStatus.OK
    assert payload["read_only"] is True


def test_a_writable_knob_is_not_readable_over_get() -> None:
    made = _routes.Router(object(), 8770)
    status, payload = made.resolve("/api/mutate/shutdown-hours")
    assert status is HTTPStatus.NOT_FOUND
    assert "POST" in payload["error"]
