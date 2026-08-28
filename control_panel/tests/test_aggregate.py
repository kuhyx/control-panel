from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from control_panel import _aggregate, _manifest, _systemctl
from control_panel._types import Arming, Category
from control_panel.tests import _fixture_fleet as fleet
from control_panel.tests._fixture_runner import FakeRunner, ok, show_blocks

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def tiny_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the loader at a two-subsystem fleet."""
    import json

    base = tmp_path / "manifest"
    (base / "subsystems").mkdir(parents=True)
    (base / "fleet.json").write_text(json.dumps({"order": ["alpha"]}))
    (base / "subsystems/alpha.json").write_text(
        json.dumps(
            {
                "id": "alpha",
                "title": "Alpha",
                "category": "enforcement",
                "units": [{"name": "a.timer", "scope": "user", "kind": "timer"}],
                "logs": [
                    {"id": "a-log", "kind": "file", "path": "/var/log/a.log"},
                    {
                        "id": "ajournal",
                        "kind": "journal",
                        "unit": "a.service",
                        "scope": "user",
                    },
                ],
                "facts": {"note": "why alpha exists"},
            }
        )
    )
    (base / "subsystems/beta.json").write_text(
        json.dumps({"id": "beta", "title": "Beta", "category": "server", "units": []})
    )
    monkeypatch.setattr(_manifest, "MANIFEST_DIR", base)


def _runner() -> FakeRunner:
    argv = (
        "systemctl",
        "--user",
        "show",
        "a.timer",
        "--no-pager",
        f"-p{','.join(_systemctl.SHOW_PROPERTIES)}",
    )
    empty = (
        "systemctl",
        "show",
        "--no-pager",
        f"-p{','.join(_systemctl.SHOW_PROPERTIES)}",
    )
    return FakeRunner(
        {
            argv: ok(argv, show_blocks([{"Id": "a.timer", "LoadState": "loaded"}])),
            empty: ok(empty, ""),
        }
    )


def test_builds_a_complete_payload(tiny_manifest: None, sysroot: Path) -> None:
    log = sysroot / "var/log/a.log"
    log.parent.mkdir(parents=True)
    log.write_text("hello\n")
    status = _aggregate.build_status(_runner(), 8770)
    assert status.schema_version == 1
    assert status.port == 8770
    assert [s.id for s in status.subsystems] == ["alpha", "beta"]
    assert status.rollup[Arming.UNARMED] == 1
    assert status.collector.duration_ms >= 0


def test_log_refs_are_stat_only(tiny_manifest: None, sysroot: Path) -> None:
    log = sysroot / "var/log/a.log"
    log.parent.mkdir(parents=True)
    log.write_text("x" * 1234)
    status = _aggregate.build_status(_runner(), 8770)
    logs = {ref.id: ref for ref in status.subsystems[0].logs}
    assert logs["a-log"].bytes == 1234
    assert logs["a-log"].rotated is False
    assert logs["ajournal"].kind == "journal"
    assert logs["ajournal"].unit == "a.service"


def test_facts_are_carried_through(tiny_manifest: None) -> None:
    status = _aggregate.build_status(_runner(), 8770)
    assert status.subsystems[0].facts["note"] == "why alpha exists"


def test_a_subsystem_with_no_units_says_so(tiny_manifest: None) -> None:
    status = _aggregate.build_status(_runner(), 8770)
    beta = next(s for s in status.subsystems if s.id == "beta")
    assert beta.state is Arming.ARMED
    assert "another mechanism" in beta.reason
    assert beta.category is Category.SERVER


def test_reason_names_the_failing_units(tiny_manifest: None) -> None:
    status = _aggregate.build_status(_runner(), 8770)
    alpha = status.subsystems[0]
    assert alpha.state is Arming.UNARMED
    assert "a.timer" in alpha.reason


def test_all_armed_reason_counts_units() -> None:
    from control_panel._types import Scope, UnitRecord

    records = (UnitRecord(name="x", scope=Scope.USER, arming=Arming.ARMED),)
    assert (
        _aggregate._reason_for(Arming.ARMED, records) == "all 1 declared unit(s) armed"
    )


def test_degraded_collector_when_systemd_returns_nothing(tiny_manifest: None) -> None:
    status = _aggregate.build_status(FakeRunner({}), 8770)
    assert status.collector.degraded


def test_not_degraded_when_listings_return_rows(
    tiny_manifest: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from control_panel import _collect

    monkeypatch.setattr(
        _collect,
        "read_systemd",
        lambda _runner: fleet.view(
            user_files={"a.timer": ("enabled", "enabled")},
            system_files={"z.service": ("enabled", "enabled")},
            user_timers={"a.timer": 42},
        ),
    )
    status = _aggregate.build_status(_runner(), 8770)
    assert not status.collector.degraded
    assert status.subsystems[0].state is Arming.ARMED
