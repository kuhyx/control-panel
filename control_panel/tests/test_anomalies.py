from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from control_panel import _anomalies
from control_panel._types import (
    Arming,
    Category,
    Level,
    LogRef,
    Scope,
    SubsystemStatus,
    UnitRecord,
)
from control_panel.tests import _fixture_fleet as fleet

if TYPE_CHECKING:
    import pytest

MB = 1024 * 1024


_BASE = SubsystemStatus(
    id="s", title="S", category=Category.ENFORCEMENT, state=Arming.ARMED
)


def subsystem(**changes: object) -> SubsystemStatus:
    return replace(_BASE, **changes)


def record(name: str, arming: Arming) -> UnitRecord:
    return UnitRecord(
        name=name, scope=Scope.USER, arming=arming, arming_reason=("because",)
    )


def test_armed_and_retired_units_raise_nothing() -> None:
    status = subsystem(
        units=(record("a.timer", Arming.ARMED), record("b.timer", Arming.RETIRED))
    )
    assert _anomalies.detect((), (status,), fleet.view()) == ()


def test_each_failing_state_raises_at_the_right_severity() -> None:
    status = subsystem(
        units=(
            record("bad.service", Arming.BAD),
            record("missing.timer", Arming.NOT_INSTALLED),
            record("off.timer", Arming.UNARMED),
            record("stalled.timer", Arming.DEGRADED),
            record("mystery.service", Arming.UNKNOWN),
        )
    )
    found = _anomalies.detect((), (status,), fleet.view())
    severities = {a.id: a.severity for a in found}
    assert severities["bad-service-bad"] is Level.DANGER
    assert severities["missing-timer-not_installed"] is Level.DANGER
    assert severities["off-timer-unarmed"] is Level.WARN
    assert severities["stalled-timer-degraded"] is Level.WARN
    assert severities["mystery-service-unknown"] is Level.WARN
    # Danger first: the ordering is what makes the banner readable.
    assert [a.severity for a in found][:2] == [Level.DANGER, Level.DANGER]


def test_template_instance_names_are_slugged() -> None:
    status = subsystem(units=(record("guard-file@hosts.path", Arming.UNARMED),))
    found = _anomalies.detect((), (status,), fleet.view())
    assert found[0].id == "guard-file-at-hosts-path-unarmed"


def test_undeclared_bad_unit_is_found_by_the_fleet_sweep() -> None:
    # code-tunnel.service belongs to no subsystem, so a manifest walk never
    # reaches it.
    view = fleet.view(bad_user=frozenset({"code-tunnel.service"}))
    found = _anomalies.detect((), (), view)
    assert found[0].id == "undeclared-bad-code-tunnel-service"
    assert found[0].subsystem == ""


def test_a_declared_bad_unit_is_not_double_reported() -> None:
    entries = (fleet.entry(units=(fleet.service("code-tunnel.service"),)),)
    view = fleet.view(bad_user=frozenset({"code-tunnel.service"}))
    found = _anomalies.detect(entries, (), view)
    assert found == ()


def test_unrotated_logs_escalate_by_size() -> None:
    status = subsystem(
        logs=(
            LogRef(
                id="huge", kind="file", path="/var/log/h", bytes=40 * MB, rotated=False
            ),
            LogRef(
                id="big", kind="file", path="/var/log/b", bytes=6 * MB, rotated=False
            ),
            LogRef(
                id="small", kind="file", path="/var/log/s", bytes=1 * MB, rotated=False
            ),
        )
    )
    found = {a.id: a.severity for a in _anomalies.detect((), (status,), fleet.view())}
    assert found["log-unrotated-huge"] is Level.DANGER
    assert found["log-unrotated-big"] is Level.WARN
    assert "log-unrotated-small" not in found


def test_a_rotated_but_enormous_log_is_a_different_finding() -> None:
    # 57 MB WITH a logrotate entry means rotation is configured and not
    # working -- which no size threshold alone would tell you.
    status = subsystem(
        logs=(
            LogRef(
                id="hosts", kind="file", path="/var/log/h", bytes=54 * MB, rotated=True
            ),
        )
    )
    found = _anomalies.detect((), (status,), fleet.view())
    assert found[0].id == "log-rotation-ineffective-hosts"


def test_a_rotated_normal_log_is_silent() -> None:
    status = subsystem(
        logs=(
            LogRef(id="ok", kind="file", path="/var/log/o", bytes=1000, rotated=True),
        )
    )
    assert _anomalies.detect((), (status,), fleet.view()) == ()


def test_journal_and_sizeless_logs_are_skipped() -> None:
    status = subsystem(
        logs=(
            LogRef(id="j", kind="journal", unit="x.service"),
            LogRef(id="f", kind="file", path="/var/log/f", bytes=None),
        )
    )
    assert _anomalies.detect((), (status,), fleet.view()) == ()


def test_orphaned_unit_snapshots_are_reported(sysroot: Path) -> None:
    snap = sysroot / "home/tester/.config/systemd/user/disabled-2026-08-21"
    snap.mkdir(parents=True)
    entries = (fleet.entry(snapshot_dirs=("~/.config/systemd/user/disabled-*",)),)
    found = _anomalies.detect(entries, (), fleet.view())
    assert found[0].id == "orphaned-unit-snapshot-disabled-2026-08-21"
    assert found[0].severity is Level.INFO


def test_absolute_snapshot_patterns_also_work(sysroot: Path) -> None:
    (sysroot / "etc/saved-units").mkdir(parents=True)
    entries = (fleet.entry(snapshot_dirs=("/etc/saved-*",)),)
    found = _anomalies.detect(entries, (), fleet.view())
    assert found[0].id == "orphaned-unit-snapshot-saved-units"


def test_a_snapshot_pattern_matching_nothing_is_silent() -> None:
    entries = (fleet.entry(snapshot_dirs=("~/nothing-*",)),)
    assert _anomalies.detect(entries, (), fleet.view()) == ()


def test_a_bad_glob_does_not_crash_the_sweep() -> None:
    entries = (fleet.entry(snapshot_dirs=("~/**bad[",)),)
    assert _anomalies.detect(entries, (), fleet.view()) == ()


def test_an_unreadable_snapshot_directory_does_not_crash_the_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied(*_args: object, **_kwargs: object) -> None:
        msg = "permission denied"
        raise OSError(msg)

    monkeypatch.setattr(Path, "glob", denied)
    entries = (fleet.entry(snapshot_dirs=("~/whatever-*",)),)
    assert _anomalies.detect(entries, (), fleet.view()) == ()
