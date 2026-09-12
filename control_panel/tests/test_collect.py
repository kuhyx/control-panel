from __future__ import annotations

from control_panel import _collect, _systemctl
from control_panel._types import Arming, Scope
from control_panel.tests import _fixture_fleet as fleet
from control_panel.tests._fixture_runner import FakeRunner, ok, show_blocks


def show_argv(units: tuple[str, ...], *, user: bool) -> tuple[str, ...]:
    scope = ("--user",) if user else ()
    return (
        "systemctl",
        *scope,
        "show",
        *units,
        "--no-pager",
        f"-p{','.join(_systemctl.SHOW_PROPERTIES)}",
    )


def runner_for(blocks: list[dict[str, str]], units: tuple[str, ...]) -> FakeRunner:
    argv = show_argv(units, user=True)
    empty = show_argv((), user=False)
    return FakeRunner({argv: ok(argv, show_blocks(blocks)), empty: ok(empty, "")})


def test_disabled_timer_does_not_leave_its_service_looking_armed() -> None:
    # The regression this whole module exists for: TriggeredBy is a RUNTIME
    # edge, so a disabled timer reports nothing, and the `static` service it
    # fires read as ARMED while enforcement was actually off.
    entries = (
        fleet.entry(
            units=(
                fleet.timer("budget.timer"),
                fleet.service("budget.service"),
            )
        ),
    )
    units = ("budget.timer", "budget.service")
    runner = runner_for(
        [
            {"Id": "budget.timer", "LoadState": "loaded", "Unit": "budget.service"},
            {"Id": "budget.service", "LoadState": "loaded", "TriggeredBy": ""},
        ],
        units,
    )
    view = fleet.view(
        user_files={
            "budget.timer": ("disabled", "enabled"),
            "budget.service": ("static", ""),
        }
    )
    records = _collect.collect_units(runner, entries, view)["s"]
    by_name = {r.name: r for r in records}
    assert by_name["budget.timer"].arming is Arming.UNARMED
    assert by_name["budget.service"].arming is Arming.UNARMED
    assert "budget.timer" in by_name["budget.service"].arming_reason[0]


def test_armed_timer_arms_its_service() -> None:
    entries = (fleet.entry(units=(fleet.timer("t.timer"), fleet.service("t.service"))),)
    units = ("t.timer", "t.service")
    runner = runner_for(
        [
            {"Id": "t.timer", "LoadState": "loaded", "Unit": "t.service"},
            {"Id": "t.service", "LoadState": "loaded"},
        ],
        units,
    )
    view = fleet.view(
        user_files={"t.timer": ("enabled", "enabled"), "t.service": ("static", "")},
        user_timers={"t.timer": 999},
    )
    records = {r.name: r for r in _collect.collect_units(runner, entries, view)["s"]}
    assert records["t.timer"].arming is Arming.ARMED
    assert records["t.service"].arming is Arming.ARMED


def test_template_instances_are_found_via_show_not_list_unit_files() -> None:
    # list-unit-files lists guard-file@.path, never guard-file@hosts.path, so
    # all four live guards read NOT_INSTALLED without this fallback.
    entries = (fleet.entry(units=(fleet.service("guard-file@hosts.path"),)),)
    units = ("guard-file@hosts.path",)
    runner = runner_for(
        [
            {
                "Id": "guard-file@hosts.path",
                "LoadState": "loaded",
                "UnitFileState": "enabled",
                "UnitFilePreset": "disabled",
            }
        ],
        units,
    )
    record = _collect.collect_units(runner, entries, fleet.view())["s"][0]
    assert record.arming is Arming.ARMED
    assert record.installed


def test_instance_without_a_unit_file_state_is_labelled_instance() -> None:
    entries = (fleet.entry(units=(fleet.service("g@x.path"),)),)
    units = ("g@x.path",)
    runner = runner_for([{"Id": "g@x.path", "LoadState": "loaded"}], units)
    record = _collect.collect_units(runner, entries, fleet.view())["s"][0]
    assert record.state.unit_file_state == "instance"


def test_never_installed_unit_stays_not_installed() -> None:
    entries = (fleet.entry(units=(fleet.timer("phone-auto-sync.timer"),)),)
    units = ("phone-auto-sync.timer",)
    runner = runner_for([{"LoadState": "not-found"}], units)
    record = _collect.collect_units(runner, entries, fleet.view())["s"][0]
    assert record.arming is Arming.NOT_INSTALLED


def test_records_keep_manifest_order_despite_two_pass_evaluation() -> None:
    entries = (
        fleet.entry(
            units=(
                fleet.service("a.service"),
                fleet.timer("b.timer"),
                fleet.service("c.service"),
            )
        ),
    )
    units = ("a.service", "b.timer", "c.service")
    runner = runner_for(
        [
            {"Id": "a.service", "LoadState": "loaded", "TriggeredBy": "b.timer"},
            {"Id": "b.timer", "LoadState": "loaded", "Unit": "c.service"},
            {"Id": "c.service", "LoadState": "loaded"},
        ],
        units,
    )
    view = fleet.view(
        user_files={
            "a.service": ("static", ""),
            "b.timer": ("enabled", "enabled"),
            "c.service": ("static", ""),
        },
        user_timers={"b.timer": 5},
    )
    names = [r.name for r in _collect.collect_units(runner, entries, view)["s"]]
    assert names == ["a.service", "b.timer", "c.service"]


def test_read_systemd_queries_both_scopes() -> None:
    runner = FakeRunner({})
    view = _collect.read_systemd(runner)
    assert set(view.unit_files) == {Scope.USER, Scope.SYSTEM}
    assert view.is_bad("anything", Scope.USER) is False
    assert view.timer("anything", Scope.USER) is None


def test_exec_start_existence_is_checked(sysroot: object) -> None:
    entries = (fleet.entry(units=(fleet.service("gone.service"),)),)
    units = ("gone.service",)
    runner = runner_for(
        [
            {
                "Id": "gone.service",
                "LoadState": "loaded",
                "ExecStart": "{ path=/usr/bin/vanished ; argv[]=x }",
            }
        ],
        units,
    )
    view = fleet.view(user_files={"gone.service": ("enabled", "enabled")})
    record = _collect.collect_units(runner, entries, view)["s"][0]
    assert record.state.exec_start == "/usr/bin/vanished"
    assert record.state.exec_start_exists is False


def test_a_unit_declared_by_two_subsystems_is_only_asked_about_once() -> None:
    # guard-file@hosts.path plausibly belongs to both hosts and guard-lib;
    # asking systemd twice for the same unit is pure waste.
    shared = fleet.service("shared.service")
    entries = (
        fleet.entry(id="one", units=(shared,)),
        fleet.entry(id="two", units=(shared,)),
    )
    units = ("shared.service",)
    runner = runner_for([{"Id": "shared.service", "LoadState": "loaded"}], units)
    _collect.collect_units(runner, entries, fleet.view())
    show_calls = [c for c in runner.calls if "show" in c]
    # One call for the user scope; the system scope has no units, and
    # show_many makes no call at all for an empty set.
    assert len(show_calls) == 1
    assert show_calls[0].count("shared.service") == 1
