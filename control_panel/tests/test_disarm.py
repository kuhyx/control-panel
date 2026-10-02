"""Deliberate disarms and on-demand units: decisions, not faults."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from control_panel import _aggregate, _arming, _disarm, _manifest, _tray_model
from control_panel._arming import Observation
from control_panel._manifest import ManifestUnit
from control_panel._systemctl import UnitFile
from control_panel._types import Arming, Scope, UnitRecord
from control_panel.tests._fixture_runner import FakeRunner

if TYPE_CHECKING:
    from pathlib import Path

MARKER = "~/.local/share/home_guard/DISARMED"


def _marker(sysroot: Path, text: str) -> None:
    path = sysroot / "home/tester/.local/share/home_guard/DISARMED"
    path.parent.mkdir(parents=True)
    path.write_text(text)


def test_reason_requires_a_declared_existing_marker(sysroot: Path) -> None:
    assert _disarm.reason("") is None
    assert _disarm.reason(MARKER) is None
    _marker(sysroot, "  until the app is done (kuhy)\n")
    assert _disarm.reason(MARKER) == "until the app is done (kuhy)"


def test_reason_reads_absolute_markers_and_empty_files(sysroot: Path) -> None:
    path = sysroot / "var/lib/guard/DISARMED"
    path.parent.mkdir(parents=True)
    path.write_text("")
    assert _disarm.reason("/var/lib/guard/DISARMED") == "no reason recorded"


def test_apply_relabels_only_units_that_are_not_armed() -> None:
    records = (
        UnitRecord(name="a", scope=Scope.USER, arming=Arming.BAD),
        UnitRecord(name="b", scope=Scope.USER, arming=Arming.ARMED),
        UnitRecord(name="c", scope=Scope.USER, arming=Arming.RETIRED),
    )
    out = _disarm.apply(records, "why")
    assert [r.arming for r in out] == [Arming.DISARMED, Arming.ARMED, Arming.RETIRED]
    assert out[0].arming_reason[-1] == "deliberately disarmed: why"


def test_disarmed_ranks_between_unknown_and_retired() -> None:
    from control_panel._types import worst_arming

    assert worst_arming((Arming.DISARMED, Arming.ARMED)) is Arming.DISARMED
    assert worst_arming((Arming.DISARMED, Arming.UNKNOWN)) is Arming.UNKNOWN


def test_disarmed_is_healthy_for_the_tray() -> None:
    assert _tray_model.level_of({"state": Arming.DISARMED}) == "ok"


def test_on_demand_service_is_armed_while_disabled() -> None:
    declared = ManifestUnit(
        name="m.service", scope=Scope.USER, kind="service", on_demand=True
    )
    unit_file = UnitFile(name="m.service", state="disabled", preset="enabled")
    record = _arming.evaluate(Observation(declared=declared, unit_file=unit_file))
    assert record.arming is Arming.ARMED
    assert "on demand" in record.arming_reason[-1]


@pytest.fixture
def guarded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A one-subsystem fleet whose only unit is masked, with a marker declared."""
    base = tmp_path / "manifest"
    (base / "subsystems").mkdir(parents=True)
    (base / "fleet.json").write_text(json.dumps({"order": ["g"]}))
    (base / "subsystems/g.json").write_text(
        json.dumps(
            {
                "id": "g",
                "title": "G",
                "category": "enforcement",
                "disarm_marker": MARKER,
                "units": [{"name": "g.timer", "scope": "user", "kind": "timer"}],
            }
        )
    )
    monkeypatch.setattr(_manifest, "MANIFEST_DIR", base)


def test_aggregate_reports_the_owners_reason(guarded: None, sysroot: Path) -> None:
    del guarded
    unarmed = _aggregate.build_status(FakeRunner({}), 8760).subsystems[0]
    assert unarmed.state is Arming.NOT_INSTALLED
    _marker(sysroot, "until the app is done (kuhy)")
    disarmed = _aggregate.build_status(FakeRunner({}), 8760).subsystems[0]
    assert disarmed.state is Arming.DISARMED
    assert disarmed.reason == "disarmed on purpose: until the app is done (kuhy)"
    assert _manifest.load_manifest()[0].live.disarm_marker == MARKER


def _stash_fleet(sysroot: Path) -> tuple[object, ...]:
    from control_panel._manifest import ManifestLive
    from control_panel.tests import _fixture_fleet as fleet

    snap = sysroot / "home/tester/.config/systemd/user/disabled-20260912-135632"
    snap.mkdir(parents=True)
    (snap / "home-guard-gate.timer").write_text("[Timer]\n")
    guard = fleet.entry(
        id="home-guard",
        units=(fleet.timer("home-guard-gate.timer"),),
        live=ManifestLive(disarm_marker=MARKER),
    )
    locker = fleet.entry(snapshot_dirs=("~/.config/systemd/user/disabled-*",))
    return (guard, locker)


def test_a_disarm_stash_is_not_an_orphan(sysroot: Path) -> None:
    from control_panel import _anomalies
    from control_panel.tests import _fixture_fleet as fleet

    entries = _stash_fleet(sysroot)
    orphan = _anomalies.detect(entries, (), fleet.view())
    assert [a.id for a in orphan] == ["orphaned-unit-snapshot-disabled-20260912-135632"]
    _marker(sysroot, "until the app is done (kuhy)")
    assert _anomalies.detect(entries, (), fleet.view()) == ()


def test_an_unreadable_snapshot_still_counts_as_orphaned(
    sysroot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path as RealPath

    from control_panel import _anomalies

    entries = _stash_fleet(sysroot)
    _marker(sysroot, "why")

    def denied(_self: object) -> None:
        msg = "permission denied"
        raise OSError(msg)

    monkeypatch.setattr(RealPath, "iterdir", denied)
    from control_panel.tests import _fixture_fleet as fleet

    assert len(_anomalies.detect(entries, (), fleet.view())) == 1
