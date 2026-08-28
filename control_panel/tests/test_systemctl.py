from __future__ import annotations

from control_panel import _systemctl
from control_panel._types import Scope
from control_panel.tests._fixture_runner import (
    FakeRunner,
    ok,
    show_blocks,
    timers_json,
    unit_files_json,
)

_UF_SYSTEM = (
    "systemctl",
    "list-unit-files",
    "--no-pager",
    "--output=json",
    "--type=service,timer,path",
)
_UF_USER = (
    "systemctl",
    "--user",
    "list-unit-files",
    "--no-pager",
    "--output=json",
    "--type=service,timer,path",
)
_TIMERS = ("systemctl", "list-timers", "--all", "--no-pager", "--output=json")
_BAD_USER = (
    "systemctl",
    "--user",
    "list-unit-files",
    "--state=bad",
    "--no-pager",
    "--output=json",
)


def test_list_unit_files_parses_rows() -> None:
    runner = FakeRunner(
        {
            _UF_SYSTEM: ok(
                _UF_SYSTEM, unit_files_json([("dufs.service", "enabled", "disabled")])
            )
        }
    )
    files = _systemctl.list_unit_files(runner, Scope.SYSTEM)
    assert files["dufs.service"].state == "enabled"
    assert files["dufs.service"].preset == "disabled"


def test_user_scope_adds_the_user_flag() -> None:
    runner = FakeRunner({_UF_USER: ok(_UF_USER, "[]")})
    _systemctl.list_unit_files(runner, Scope.USER)
    assert runner.calls == [_UF_USER]


def test_failed_listing_yields_empty_rather_than_raising() -> None:
    assert _systemctl.list_unit_files(FakeRunner({}), Scope.SYSTEM) == {}
    assert _systemctl.list_timers(FakeRunner({}), Scope.SYSTEM) == {}
    assert _systemctl.list_bad_units(FakeRunner({}), Scope.SYSTEM) == frozenset()
    assert _systemctl.cat(FakeRunner({}), "x.service", Scope.SYSTEM) == ""


def test_malformed_json_yields_empty() -> None:
    runner = FakeRunner({_UF_SYSTEM: ok(_UF_SYSTEM, "not json at all")})
    assert _systemctl.list_unit_files(runner, Scope.SYSTEM) == {}


def test_non_array_json_yields_empty() -> None:
    runner = FakeRunner({_UF_SYSTEM: ok(_UF_SYSTEM, '{"unit_file": "x"}')})
    assert _systemctl.list_unit_files(runner, Scope.SYSTEM) == {}


def test_rows_without_a_name_are_skipped() -> None:
    runner = FakeRunner({_UF_SYSTEM: ok(_UF_SYSTEM, '[{"state": "enabled"}, 3]')})
    assert _systemctl.list_unit_files(runner, Scope.SYSTEM) == {}


def test_timer_without_next_elapse_is_none() -> None:
    payload = timers_json(
        [("armed.timer", 123, "armed.service"), ("stalled.timer", None, "s.service")]
    )
    runner = FakeRunner({_TIMERS: ok(_TIMERS, payload)})
    timers = _systemctl.list_timers(runner, Scope.SYSTEM)
    assert timers["armed.timer"].next_elapse == 123
    assert timers["stalled.timer"].next_elapse is None


def test_timer_rows_without_a_unit_are_skipped() -> None:
    runner = FakeRunner({_TIMERS: ok(_TIMERS, '[{"next": 1}]')})
    assert _systemctl.list_timers(runner, Scope.SYSTEM) == {}


def test_zero_and_non_int_timestamps_read_as_none() -> None:
    payload = '[{"unit": "t.timer", "next": 0, "last": true, "activates": 5}]'
    runner = FakeRunner({_TIMERS: ok(_TIMERS, payload)})
    row = _systemctl.list_timers(runner, Scope.SYSTEM)["t.timer"]
    assert row.next_elapse is None
    assert row.last_trigger is None
    assert row.activates is None


def test_bad_units_are_listed() -> None:
    payload = unit_files_json([("code-tunnel.service", "bad", "enabled")])
    runner = FakeRunner({_BAD_USER: ok(_BAD_USER, payload)})
    assert _systemctl.list_bad_units(runner, Scope.USER) == frozenset(
        {"code-tunnel.service"}
    )


def test_show_many_batches_into_one_call() -> None:
    units = ("a.service", "b.timer")
    argv = (
        "systemctl",
        "show",
        *units,
        "--no-pager",
        f"-p{','.join(_systemctl.SHOW_PROPERTIES)}",
    )
    body = show_blocks(
        [
            {"Id": "a.service", "LoadState": "loaded"},
            {"Id": "b.timer", "LoadState": "loaded", "UnitFileState": "enabled"},
        ]
    )
    runner = FakeRunner({argv: ok(argv, body)})
    props = _systemctl.show_many(runner, units, Scope.SYSTEM)
    assert len(runner.calls) == 1
    assert props["a.service"]["LoadState"] == "loaded"
    assert props["b.timer"]["UnitFileState"] == "enabled"


def test_show_many_with_no_units_makes_no_call() -> None:
    runner = FakeRunner({})
    assert _systemctl.show_many(runner, (), Scope.SYSTEM) == {}
    assert runner.calls == []


def test_show_many_failure_yields_empty() -> None:
    assert _systemctl.show_many(FakeRunner({}), ("a.service",), Scope.SYSTEM) == {}


def test_show_many_indexes_by_canonical_id_too() -> None:
    units = ("alias.service",)
    argv = (
        "systemctl",
        "show",
        *units,
        "--no-pager",
        f"-p{','.join(_systemctl.SHOW_PROPERTIES)}",
    )
    body = show_blocks([{"Id": "real.service", "LoadState": "loaded"}])
    runner = FakeRunner({argv: ok(argv, body)})
    props = _systemctl.show_many(runner, units, Scope.SYSTEM)
    assert props["alias.service"] == props["real.service"]


def test_show_many_block_without_id_is_kept_under_requested_name() -> None:
    units = ("ghost.service",)
    argv = (
        "systemctl",
        "show",
        *units,
        "--no-pager",
        f"-p{','.join(_systemctl.SHOW_PROPERTIES)}",
    )
    runner = FakeRunner({argv: ok(argv, "LoadState=not-found")})
    props = _systemctl.show_many(runner, units, Scope.SYSTEM)
    assert props["ghost.service"]["LoadState"] == "not-found"


def test_cat_returns_unit_text() -> None:
    argv = ("systemctl", "cat", "x.service", "--no-pager")
    runner = FakeRunner({argv: ok(argv, "# why\n[Unit]\n")})
    assert "# why" in _systemctl.cat(runner, "x.service", Scope.SYSTEM)


def test_property_blocks_tolerate_lines_without_an_equals_sign() -> None:
    units = ("a.service",)
    argv = (
        "systemctl",
        "show",
        *units,
        "--no-pager",
        f"-p{','.join(_systemctl.SHOW_PROPERTIES)}",
    )
    runner = FakeRunner({argv: ok(argv, "Id=a.service\ngarbage line\nResult=success")})
    props = _systemctl.show_many(runner, units, Scope.SYSTEM)
    assert props["a.service"] == {"Id": "a.service", "Result": "success"}
