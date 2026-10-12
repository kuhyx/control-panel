"""Routes added for the server fleet: journal, unknown, tray, restart.

Split from test_routes.py, which was near the 250-line cap.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

import pytest

from control_panel import _journal, _manifest, _routes, _unknown
from control_panel._manifest import ManifestLog
from control_panel._types import Scope
from control_panel.tests import _fixture_fleet as fleet
from control_panel.tests._fixture_runner import FakeRunner, ok

STATUS: dict[str, Any] = {
    "subsystems": [
        {
            "id": "alpha",
            "title": "Alpha",
            "state": "ARMED",
            "important": True,
            "dashboards": [],
            "logs": [
                {"id": "uj", "kind": "journal", "unit": "a.service", "scope": "user"},
                {"id": "sj", "kind": "journal", "unit": "b.service", "scope": None},
            ],
        }
    ]
}
ENTRY = fleet.entry(
    units=(fleet.service("a.service"),),
    logs=(
        ManifestLog(id="uj", kind="journal", unit="a.service", scope=Scope.USER),
        ManifestLog(id="sj", kind="journal", unit="b.service"),
    ),
)


@pytest.fixture
def router(monkeypatch: pytest.MonkeyPatch) -> _routes.Router:
    monkeypatch.setattr(_routes.Router, "_status", lambda _self, **_kw: STATUS)
    monkeypatch.setattr(_manifest, "load_manifest", lambda: (ENTRY,))
    argv = _journal.argv_for("user", "a.service", 100)
    return _routes.Router(FakeRunner({argv: ok(argv, "line\n")}), 8760)


def test_journal_route_reads_a_declared_unit(router: _routes.Router) -> None:
    status, payload = router.resolve("/api/journal/user/a.service")
    assert status is HTTPStatus.OK
    assert payload["lines"] == ["line"]


def test_journal_route_404s_undeclared_and_malformed(router: _routes.Router) -> None:
    status, payload = router.resolve("/api/journal/system/sshd.service")
    assert status is HTTPStatus.NOT_FOUND
    assert "not declared" in payload["error"]
    status, _ = router.resolve("/api/journal/user")
    assert status is HTTPStatus.NOT_FOUND


def test_journal_kind_logs_are_read(router: _routes.Router) -> None:
    status, payload = router.resolve("/api/logs/uj")
    assert status is HTTPStatus.OK
    assert payload["lines"] == ["line"]


def test_a_journal_log_without_scope_reads_the_system_journal(
    router: _routes.Router,
) -> None:
    # b.service is not a declared *system* unit here, so it 404s -- the point
    # is that a null scope resolved to "system" rather than raising.
    status, payload = router.resolve("/api/logs/sj")
    assert status is HTTPStatus.NOT_FOUND
    assert payload["error"] == "system/b.service is not declared"


def test_unknown_route(router: _routes.Router, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []

    def listeners(
        _runner: object, _entries: object, _ignored: object, port: int
    ) -> list[Any]:
        seen.append(port)
        return []

    monkeypatch.setattr(_unknown, "unknown_listeners", listeners)
    monkeypatch.setattr(_manifest, "load_ignored_listeners", tuple)
    status, payload = router.resolve("/api/unknown")
    assert status is HTTPStatus.OK
    assert payload == {"listeners": [], "units": []}
    assert seen == [8760]


def test_tray_route(router: _routes.Router) -> None:
    status, payload = router.resolve("/api/tray")
    assert status is HTTPStatus.OK
    assert payload["level"] == "ok"
    assert payload["panel_url"] == "http://127.0.0.1:8760/"
    assert payload["items"][0]["panel_url"] == "http://127.0.0.1:8760/#/s/alpha"


def test_restart_is_a_mutation(router: _routes.Router) -> None:
    status, payload = router.mutate("restart", {"kind": "unit", "name": "a.service"})
    assert status is HTTPStatus.OK
    assert payload["refused"] is True
