from __future__ import annotations

import json

import pytest

from control_panel._types import (
    Anomaly,
    Arming,
    Category,
    Collector,
    FleetStatus,
    Level,
    SubsystemStatus,
    to_payload,
    worst_arming,
)


def test_worst_arming_empty_is_armed() -> None:
    assert worst_arming(()) is Arming.ARMED


@pytest.mark.parametrize(
    ("states", "expected"),
    [
        ((Arming.ARMED, Arming.BAD), Arming.BAD),
        ((Arming.ARMED, Arming.UNARMED), Arming.UNARMED),
        ((Arming.ARMED, Arming.DEGRADED), Arming.DEGRADED),
        ((Arming.UNARMED, Arming.NOT_INSTALLED), Arming.NOT_INSTALLED),
        ((Arming.ARMED, Arming.UNKNOWN), Arming.UNKNOWN),
        ((Arming.ARMED,), Arming.ARMED),
    ],
)
def test_worst_arming_picks_most_severe(
    states: tuple[Arming, ...], expected: Arming
) -> None:
    assert worst_arming(states) is expected


def test_retired_units_do_not_retire_a_live_subsystem() -> None:
    # Hosts blocking keeps five superseded guards next to three live ones.
    # Ranking RETIRED above ARMED labelled it "RETIRED" while it was enforcing.
    assert worst_arming((Arming.ARMED, Arming.RETIRED, Arming.RETIRED)) is Arming.ARMED


def test_all_retired_reports_retired() -> None:
    assert worst_arming((Arming.RETIRED, Arming.RETIRED)) is Arming.RETIRED


def test_retired_does_not_mask_a_real_fault() -> None:
    assert worst_arming((Arming.RETIRED, Arming.UNARMED)) is Arming.UNARMED


def test_payload_is_json_serialisable() -> None:
    status = FleetStatus(
        schema_version=1,
        generated_at="2026-08-28T00:00:00+00:00",
        host="testbox",
        port=8770,
        collector=Collector(duration_ms=1, degraded=False, journal_readable=True),
        rollup={"ARMED": 1},
        subsystems=(
            SubsystemStatus(
                id="x",
                title="X",
                category=Category.ENFORCEMENT,
                state=Arming.ARMED,
            ),
        ),
        anomalies=(
            Anomaly(id="a", subsystem="x", severity=Level.WARN, title="t", detail="d"),
        ),
    )
    # StrEnum members survive asdict as enum instances; they serialise only
    # because every enum here subclasses str.
    encoded = json.dumps(to_payload(status))
    assert '"state": "ARMED"' in encoded
    assert '"severity": "warn"' in encoded
