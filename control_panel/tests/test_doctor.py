from __future__ import annotations

from control_panel import _doctor
from control_panel._types import Arming, Scope, UnitRecord
from control_panel.tests import _fixture_fleet as fleet


def record(name: str, arming: Arming) -> UnitRecord:
    return UnitRecord(
        name=name, scope=Scope.USER, arming=arming, arming_reason=("why",)
    )


def test_renders_every_subsystem_and_a_tally() -> None:
    entries = (fleet.entry(id="s", title="Subsystem"),)
    units = {"s": (record("a.timer", Arming.ARMED), record("b.timer", Arming.UNARMED))}
    text = _doctor.render(entries, units, colour=False)
    assert "Subsystem" in text
    assert "a.timer" in text
    assert "ARMED=1" in text
    assert "UNARMED=1" in text
    assert "\033[" not in text


def test_colour_is_applied_when_asked() -> None:
    entries = (fleet.entry(),)
    units = {"s": (record("a.timer", Arming.ARMED),)}
    assert "\033[32m" in _doctor.render(entries, units, colour=True)


def test_a_subsystem_with_no_units_says_why() -> None:
    text = _doctor.render((fleet.entry(),), {"s": ()}, colour=False)
    assert "another mechanism" in text


def test_missing_subsystem_key_renders_as_empty() -> None:
    text = _doctor.render((fleet.entry(),), {}, colour=False)
    assert "another mechanism" in text


def test_problems_exclude_armed_and_retired() -> None:
    units = {
        "s": (
            record("ok.timer", Arming.ARMED),
            record("gone.timer", Arming.RETIRED),
            record("off.timer", Arming.UNARMED),
            record("missing.timer", Arming.NOT_INSTALLED),
        )
    }
    names = [r.name for r in _doctor.problems(units)]
    assert names == ["off.timer", "missing.timer"]
