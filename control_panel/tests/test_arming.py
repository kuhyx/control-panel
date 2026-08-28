from __future__ import annotations

from dataclasses import replace

import pytest

from control_panel import _arming
from control_panel._arming import Observation
from control_panel._manifest import ManifestUnit, Retired
from control_panel._systemctl import TimerRow, UnitFile
from control_panel._types import Arming, Scope

_BASE = ManifestUnit(name="x.service", scope=Scope.SYSTEM, kind="service")


def unit(
    name: str = "x.service", kind: str = "service", **changes: object
) -> ManifestUnit:
    return replace(_BASE, name=name, kind=kind, **changes)


def uf(state: str = "enabled", preset: str = "enabled") -> UnitFile:
    return UnitFile(name="x", state=state, preset=preset)


def test_retired_is_declared_not_computed() -> None:
    declared = unit(retired=Retired(since="2026", superseded_by="new.timer"))
    record = _arming.evaluate(Observation(declared=declared, unit_file=uf()))
    assert record.arming is Arming.RETIRED
    assert record.declared_retired
    assert "superseded by new.timer" in record.arming_reason[0]


def test_retired_but_still_enabled_says_so() -> None:
    declared = unit(retired=Retired(since="2026", superseded_by="new.timer"))
    record = _arming.evaluate(
        Observation(declared=declared, unit_file=uf(state="enabled"))
    )
    assert any("still enabled" in reason for reason in record.arming_reason)


def test_missing_unit_file_is_not_installed() -> None:
    record = _arming.evaluate(Observation(declared=unit(), unit_file=None))
    assert record.arming is Arming.NOT_INSTALLED
    assert not record.installed


@pytest.mark.parametrize("load_state", ["error", "not-found", "masked"])
def test_broken_load_state_is_bad(load_state: str) -> None:
    record = _arming.evaluate(
        Observation(declared=unit(), unit_file=uf(), props={"LoadState": load_state})
    )
    assert record.arming is Arming.BAD


def test_bad_unit_list_marks_bad() -> None:
    record = _arming.evaluate(
        Observation(declared=unit(), unit_file=uf(state="bad"), is_bad=True)
    )
    assert record.arming is Arming.BAD


def test_enabled_scheduled_timer_is_armed() -> None:
    timer = TimerRow(
        unit="t.timer", next_elapse=99, last_trigger=1, activates="t.service"
    )
    record = _arming.evaluate(
        Observation(declared=unit("t.timer", "timer"), unit_file=uf(), timer=timer)
    )
    assert record.arming is Arming.ARMED
    assert record.next_elapse == "99"
    assert record.last_trigger == "1"


def test_disabled_timer_is_unarmed() -> None:
    record = _arming.evaluate(
        Observation(declared=unit("t.timer", "timer"), unit_file=uf(state="disabled"))
    )
    assert record.arming is Arming.UNARMED
    assert any("not enabled" in r for r in record.arming_reason)


def test_enabled_timer_absent_from_list_timers_is_unarmed() -> None:
    record = _arming.evaluate(
        Observation(declared=unit("t.timer", "timer"), unit_file=uf(), timer=None)
    )
    assert record.arming is Arming.UNARMED
    assert any("list-timers" in r for r in record.arming_reason)


def test_enabled_timer_with_no_next_elapse_is_degraded_and_explains_why() -> None:
    # pc-startup-monitor.timer: systemd will not re-arm a timer whose
    # RemainAfterExit oneshot is still active.
    timer = TimerRow(
        unit="t.timer", next_elapse=None, last_trigger=1, activates="t.service"
    )
    record = _arming.evaluate(
        Observation(declared=unit("t.timer", "timer"), unit_file=uf(), timer=timer)
    )
    assert record.arming is Arming.DEGRADED
    assert any("RemainAfterExit" in r for r in record.arming_reason)


def test_degraded_timer_without_a_named_target_still_explains() -> None:
    timer = TimerRow(unit="t.timer", next_elapse=None, last_trigger=1, activates=None)
    record = _arming.evaluate(
        Observation(declared=unit("t.timer", "timer"), unit_file=uf(), timer=timer)
    )
    assert any("its unit" in r for r in record.arming_reason)


def test_service_delegates_to_an_armed_trigger() -> None:
    record = _arming.evaluate(
        Observation(
            declared=unit(),
            unit_file=uf(state="disabled"),
            triggers=("t.timer",),
            peers_armed=True,
        )
    )
    assert record.arming is Arming.ARMED
    assert "activated by t.timer" in record.arming_reason[0]


def test_service_with_only_unarmed_triggers_is_unarmed() -> None:
    record = _arming.evaluate(
        Observation(
            declared=unit(),
            unit_file=uf(state="static"),
            triggers=("t.timer",),
            peers_armed=False,
        )
    )
    assert record.arming is Arming.UNARMED


def test_undeclared_trigger_is_unknown_not_unarmed() -> None:
    # Defaulting an undeclared peer to "unarmed" would invent failures.
    record = _arming.evaluate(
        Observation(
            declared=unit(),
            unit_file=uf(state="static"),
            triggers=("mystery.timer",),
            peers_armed=None,
        )
    )
    assert record.arming is Arming.UNKNOWN
    assert "not declared in the manifest" in record.arming_reason[0]


def test_login_oneshot_is_armed_without_a_trigger() -> None:
    record = _arming.evaluate(
        Observation(declared=unit(login_oneshot=True), unit_file=uf(state="disabled"))
    )
    assert record.arming is Arming.ARMED
    assert record.login_oneshot


@pytest.mark.parametrize("state", ["enabled", "enabled-runtime", "static"])
def test_plain_service_states_that_count_as_armed(state: str) -> None:
    record = _arming.evaluate(Observation(declared=unit(), unit_file=uf(state=state)))
    assert record.arming is Arming.ARMED


def test_plain_disabled_service_is_unarmed() -> None:
    record = _arming.evaluate(
        Observation(declared=unit(), unit_file=uf(state="disabled"))
    )
    assert record.arming is Arming.UNARMED


def test_why_it_matters_is_appended() -> None:
    record = _arming.evaluate(
        Observation(declared=unit(why_it_matters="load bearing"), unit_file=uf())
    )
    assert record.arming_reason[-1] == "load bearing"


def test_missing_exec_start_is_reported() -> None:
    record = _arming.evaluate(
        Observation(declared=unit(), unit_file=uf(), exec_start_exists=False)
    )
    assert any("does not exist" in r for r in record.arming_reason)


def test_exec_start_binary_is_extracted() -> None:
    props = {
        "ExecStart": "{ path=/usr/local/bin/dufs ; argv[]=/usr/local/bin/dufs -c }"
    }
    assert _arming.exec_start_binary(props) == "/usr/local/bin/dufs"


def test_exec_start_binary_absent_returns_none() -> None:
    assert _arming.exec_start_binary({}) is None
    assert _arming.exec_start_binary({"ExecStart": "{ argv[]=x }"}) is None
    assert _arming.exec_start_binary({"ExecStart": "{ path= ; }"}) is None


def test_state_note_for_a_missing_unit_file() -> None:
    assert Observation(declared=unit(), unit_file=None).state_note == "not installed"


def test_timers_never_delegate() -> None:
    assert (
        _arming.delegates_to(unit("t.timer", "timer"), {"TriggeredBy": "a.timer"}) == ()
    )


def test_retired_units_never_delegate() -> None:
    declared = unit(retired=Retired(since="x", superseded_by="y"))
    assert _arming.delegates_to(declared, {"TriggeredBy": "a.timer"}) == ()


def test_declared_edge_beats_runtime_triggered_by() -> None:
    # TriggeredBy is empty for a DISABLED timer, which is exactly when the
    # answer matters most.
    assert _arming.delegates_to(unit(), {"TriggeredBy": ""}, ("budget.timer",)) == (
        "budget.timer",
    )


def test_triggered_by_is_used_when_no_declared_edge_exists() -> None:
    assert _arming.delegates_to(unit(), {"TriggeredBy": "a.timer b.timer"}) == (
        "a.timer",
        "b.timer",
    )


def test_manifest_arming_lives_on_is_the_last_resort() -> None:
    declared = unit(arming_lives_on=("fallback.timer",))
    assert _arming.delegates_to(declared, {}) == ("fallback.timer",)


def test_a_retired_unit_that_is_disabled_says_only_that_it_is_retired() -> None:
    declared = unit(retired=Retired(since="2026", superseded_by="new.timer"))
    record = _arming.evaluate(
        Observation(declared=declared, unit_file=uf(state="disabled"))
    )
    assert record.arming_reason == ("declared retired, superseded by new.timer",)
