"""Join the declared manifest against systemd's view, once per collection.

Two things here are not obvious and were both found by running it:

* **Delegation edges come from declared timers' ``Unit=``, not ``TriggeredBy``.**
  ``TriggeredBy`` is a runtime relationship, so a *disabled* timer contributes
  nothing to it. Trusting it made ``kuhytrack-budget.service`` report ARMED
  (``static``) while the timer that fires it was off.
* **Evaluation runs in two passes.** Timers never delegate, so evaluating every
  non-delegating unit first and resolving delegates against that map terminates
  without cycle detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from control_panel import _arming, _sysroot, _systemctl
from control_panel._types import Arming, Scope, UnitRecord

if TYPE_CHECKING:
    from control_panel._manifest import ManifestEntry, ManifestUnit
    from control_panel._runner import CommandRunner

UnitKey = tuple[str, Scope]


@dataclass(frozen=True, slots=True)
class SystemdView:
    """Everything read from systemd for one collection, both scopes."""

    unit_files: dict[Scope, dict[str, _systemctl.UnitFile]]
    timers: dict[Scope, dict[str, _systemctl.TimerRow]]
    bad: dict[Scope, frozenset[str]]

    def unit_file(self, name: str, scope: Scope) -> _systemctl.UnitFile | None:
        """Look up one unit file, or None when it is not installed."""
        return self.unit_files[scope].get(name)

    def timer(self, name: str, scope: Scope) -> _systemctl.TimerRow | None:
        """Look up one timer row, or None when systemd is not tracking it."""
        return self.timers[scope].get(name)

    def is_bad(self, name: str, scope: Scope) -> bool:
        """Report whether systemd could not parse this unit file."""
        return name in self.bad[scope]


@dataclass(frozen=True, slots=True)
class _Resolved:
    """One unit's ``show`` properties plus its resolved unit-file identity."""

    props: dict[str, str]
    unit_file: _systemctl.UnitFile | None
    triggers: tuple[str, ...] = ()


def read_systemd(runner: CommandRunner) -> SystemdView:
    """Run the three systemd listings for both scopes: 6 forks, once."""
    return SystemdView(
        unit_files={s: _systemctl.list_unit_files(runner, s) for s in Scope},
        timers={s: _systemctl.list_timers(runner, s) for s in Scope},
        bad={s: _systemctl.list_bad_units(runner, s) for s in Scope},
    )


def _show_all(
    runner: CommandRunner, entries: tuple[ManifestEntry, ...]
) -> dict[UnitKey, dict[str, str]]:
    """Fetch ``show`` properties for every declared unit in two forks total."""
    wanted: dict[Scope, list[str]] = {scope: [] for scope in Scope}
    for entry in entries:
        for declared in entry.units:
            if declared.name not in wanted[declared.scope]:
                wanted[declared.scope].append(declared.name)
    props: dict[UnitKey, dict[str, str]] = {}
    for scope, names in wanted.items():
        blocks = _systemctl.show_many(runner, tuple(names), scope)
        for name in names:
            props[name, scope] = blocks.get(name, {})
    return props


def _resolve_unit_file(
    declared: ManifestUnit, view: SystemdView, props: dict[str, str]
) -> _systemctl.UnitFile | None:
    """Find the unit file, falling back to ``show`` for template instances.

    ``list-unit-files`` lists the *template* ``guard-file@.path``, never the
    instances ``guard-file@hosts.path`` and friends -- so all four live
    guard-lib instances read as NOT_INSTALLED from that query alone. When the
    listing misses a unit, ``systemctl show`` is authoritative: a genuinely
    absent unit reports ``LoadState=not-found``, which is exactly how
    ``phone-auto-sync.timer`` still comes back NOT_INSTALLED here.
    """
    found = view.unit_file(declared.name, declared.scope)
    if found is not None:
        return found
    if props.get("LoadState") != "loaded":
        return None
    return _systemctl.UnitFile(
        name=declared.name,
        state=props.get("UnitFileState", "") or "instance",
        preset=props.get("UnitFilePreset", ""),
    )


def _activation_edges(
    entries: tuple[ManifestEntry, ...], props: dict[UnitKey, dict[str, str]]
) -> dict[UnitKey, tuple[str, ...]]:
    """Map each activated unit to the declared timers that activate it.

    Built from the *timer's* ``Unit=`` property, which systemd reports whether
    or not the timer is enabled -- unlike ``TriggeredBy`` on the target, which
    is empty for a disabled timer.
    """
    edges: dict[UnitKey, list[str]] = {}
    for entry in entries:
        for declared in entry.units:
            if declared.kind != "timer":
                continue
            target = props.get((declared.name, declared.scope), {}).get("Unit", "")
            if target:
                edges.setdefault((target, declared.scope), []).append(declared.name)
    return {key: tuple(names) for key, names in edges.items()}


def _exec_start_exists(props: dict[str, str]) -> bool | None:
    """Report whether the unit's ExecStart binary is present on disk."""
    binary = _arming.exec_start_binary(props)
    if binary is None:
        return None
    return _sysroot.exists(binary)


def collect_units(
    runner: CommandRunner, entries: tuple[ManifestEntry, ...], view: SystemdView
) -> dict[str, tuple[UnitRecord, ...]]:
    """Evaluate every declared unit, resolving delegation in a second pass."""
    resolved, delegating, direct = _resolve_declarations(runner, entries, view)

    records: dict[str, list[UnitRecord]] = {}
    # Keyed by (name, scope): a user unit and a system unit can share a name,
    # and collapsing them would let one scope's arming answer for the other's.
    armed: dict[UnitKey, bool] = {}
    for entry_id, declarations in direct.items():
        records[entry_id] = []
        for declared in declarations:
            record = _evaluate(declared, view, resolved, peers_armed=None)
            records[entry_id].append(record)
            armed[declared.name, declared.scope] = record.arming is Arming.ARMED

    for entry_id, declared in delegating:
        records[entry_id].append(
            _evaluate(
                declared,
                view,
                resolved,
                peers_armed=_peers_armed(declared, resolved, armed),
            )
        )

    return {entry.id: _in_declared_order(entry, records[entry.id]) for entry in entries}


def _resolve_declarations(
    runner: CommandRunner, entries: tuple[ManifestEntry, ...], view: SystemdView
) -> tuple[
    dict[UnitKey, _Resolved],
    list[tuple[str, ManifestUnit]],
    dict[str, list[ManifestUnit]],
]:
    """Read every unit once and sort the declarations into direct vs delegating."""
    raw = _show_all(runner, entries)
    edges = _activation_edges(entries, raw)
    resolved: dict[UnitKey, _Resolved] = {}
    delegating: list[tuple[str, ManifestUnit]] = []
    direct: dict[str, list[ManifestUnit]] = {}

    for entry in entries:
        direct[entry.id] = []
        for declared in entry.units:
            key = (declared.name, declared.scope)
            props = raw[key]
            triggers = _arming.delegates_to(declared, props, edges.get(key, ()))
            resolved[key] = _Resolved(
                props=props,
                unit_file=_resolve_unit_file(declared, view, props),
                triggers=triggers,
            )
            if triggers:
                delegating.append((entry.id, declared))
            else:
                direct[entry.id].append(declared)
    return resolved, delegating, direct


def _peers_armed(
    declared: ManifestUnit,
    resolved: dict[UnitKey, _Resolved],
    armed: dict[UnitKey, bool],
) -> bool | None:
    """Whether any declared trigger of a delegating unit is armed.

    None, not False, when no trigger is declared: an undeclared peer has
    unknown arming, and defaulting it to "unarmed" would invent failures.
    """
    peers = resolved[declared.name, declared.scope].triggers
    known = [
        armed[peer, declared.scope] for peer in peers if (peer, declared.scope) in armed
    ]
    return any(known) if known else None


def _in_declared_order(
    entry: ManifestEntry, records: list[UnitRecord]
) -> tuple[UnitRecord, ...]:
    """Restore manifest order, which the two-pass evaluation scrambles."""
    by_name = {record.name: record for record in records}
    return tuple(by_name[declared.name] for declared in entry.units)


def _evaluate(
    declared: ManifestUnit,
    view: SystemdView,
    resolved: dict[UnitKey, _Resolved],
    *,
    peers_armed: bool | None,
) -> UnitRecord:
    """Evaluate one declared unit against the systemd view."""
    entry = resolved[declared.name, declared.scope]
    return _arming.evaluate(
        _arming.Observation(
            declared=declared,
            unit_file=entry.unit_file,
            timer=view.timer(declared.name, declared.scope),
            props=entry.props,
            is_bad=view.is_bad(declared.name, declared.scope),
            triggers=entry.triggers,
            peers_armed=peers_armed,
            exec_start_exists=_exec_start_exists(entry.props),
        )
    )
