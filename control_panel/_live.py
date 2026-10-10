"""Collect the running half of each subsystem: dashboards, probes, containers.

Kept apart from :mod:`control_panel._aggregate` so the arming roll-up there
stays about systemd, and this module owns the one new rule: **what a failed
probe means.** On a ``server`` subsystem nothing answering *is* the outage, so
it is BAD. On an enforcement subsystem the web UI is a convenience beside the
real mechanism, so a dead one is only DEGRADED. A dashboard whose port is held
by a foreign unit or container (see :mod:`control_panel._port_owner`) counts
as dead the same way, whatever the probe says.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from control_panel import _docker, _port_owner, _probe, _unknown
from control_panel._live_types import ContainerRecord, DashboardRecord, ProbeRecord
from control_panel._types import Arming, Category

if TYPE_CHECKING:
    from collections.abc import Mapping

    from control_panel._manifest import ManifestEntry
    from control_panel._manifest_live import ManifestDashboard
    from control_panel._runner import CommandRunner
    from control_panel._types import UnitRecord

# ActiveState values that mean nothing of the unit is running.
_AT_REST = frozenset({"inactive", "failed"})


@dataclass(frozen=True, slots=True)
class LiveView:
    """One subsystem's running state."""

    dashboards: tuple[DashboardRecord, ...] = ()
    probes: tuple[ProbeRecord, ...] = ()
    containers: tuple[ContainerRecord, ...] = ()
    # Declared, not observed -- carried here so the API payload can merge one
    # record per subsystem (see _types.to_payload).
    important: bool = True


_SKIPPED = ProbeRecord(kind="http", target="", up=None, detail="not probed: on demand")


def _targets(entries: tuple[ManifestEntry, ...]) -> list[tuple[str, str]]:
    """Every probe target in the fleet, dashboards included."""
    targets: list[tuple[str, str]] = []
    for entry in entries:
        targets.extend((p.kind, p.target) for p in entry.live.probes)
        targets.extend(
            ("http", d.url) for d in entry.live.dashboards if not d.on_demand
        )
    return targets


def _read_listeners(
    runner: CommandRunner, entries: tuple[ManifestEntry, ...]
) -> _port_owner.Listeners:
    """Run ``ss -ltnpH`` once, and only if some dashboard is on loopback."""
    urls = [d.url for e in entries for d in e.live.dashboards]
    if all(_port_owner.listening(url, {}) is None for url in urls):
        return {}
    result = runner.run(_unknown.SS_ARGV)
    return _port_owner.parse_listeners(result.stdout) if result.ok else {}


def _at_rest(entry: ManifestEntry, records: tuple[UnitRecord, ...]) -> bool:
    """Whether every unit that runs this UI is known to be inactive.

    The on-demand units when any are declared (mangatl), else all of them:
    book-guard's UI is a desktop app beside always-running timers, so it is
    never "stopped" by this rule. An unread ActiveState is not "inactive".
    """
    on_demand = {u.name for u in entry.units if u.on_demand}
    relevant = [r for r in records if not on_demand or r.name in on_demand]
    return bool(relevant) and all(r.state.active_state in _AT_REST for r in relevant)


@dataclass(frozen=True, slots=True)
class _Observed:
    """What one collection saw, shared by every dashboard record."""

    results: dict[tuple[str, str], ProbeRecord]
    listeners: _port_owner.Listeners
    resolve: _port_owner.OwnerResolver
    units: Mapping[str, tuple[UnitRecord, ...]] | None


def _dashboard(
    entry: ManifestEntry, declared: ManifestDashboard, seen: _Observed
) -> DashboardRecord:
    """Build one dashboard record: probe, foreign port owner, stopped."""
    clash = _port_owner.clash(entry, declared.url, seen.listeners, seen.resolve)
    # Its own server is up when something non-foreign listens on the port: a
    # mangatl started by hand in a terminal runs with its unit inactive.
    served = bool(_port_owner.listening(declared.url, seen.listeners)) and not clash
    records = seen.units.get(entry.id) if seen.units is not None else None
    stopped = (
        declared.on_demand
        and records is not None
        and not served
        and _at_rest(entry, records)
    )
    return DashboardRecord(
        label=declared.label,
        url=declared.url,
        probe=_SKIPPED if declared.on_demand else seen.results["http", declared.url],
        on_demand=declared.on_demand,
        stopped=stopped,
        clash=clash,
    )


def collect(
    runner: CommandRunner,
    entries: tuple[ManifestEntry, ...],
    units: Mapping[str, tuple[UnitRecord, ...]] | None = None,
) -> dict[str, LiveView]:
    """Probe everything once, concurrently, and read docker and ``ss`` once.

    ``units`` -- the collected unit records, by entry id -- lets an on-demand
    dashboard report itself stopped; without them none ever is.
    """
    results = _probe.run_all(_targets(entries))
    read = (
        _docker.read_containers(runner)
        if any(e.live.containers for e in entries)
        else ({}, {})
    )
    rows, ids = read if read is not None else (None, {})
    containers = _docker.collect(entries, rows)
    seen = _Observed(
        results=results,
        listeners=_read_listeners(runner, entries),
        resolve=_port_owner.OwnerResolver(ids),
        units=units,
    )
    views: dict[str, LiveView] = {}
    for entry in entries:
        views[entry.id] = LiveView(
            dashboards=tuple(_dashboard(entry, d, seen) for d in entry.live.dashboards),
            probes=tuple(results[p.kind, p.target] for p in entry.live.probes),
            containers=containers[entry.id],
            important=entry.live.important,
        )
    return views


def states(category: Category, view: LiveView) -> tuple[Arming, ...]:
    """The arming states the running half contributes to the roll-up."""
    dead = Arming.BAD if category is Category.SERVER else Arming.DEGRADED
    probed = [p for p in view.probes if p.up is not None]
    probed += [d.probe for d in view.dashboards if d.probe.up is not None]
    found = [Arming.ARMED if p.up else dead for p in probed]
    # A foreign port owner is a dead link even when it answers the probe:
    # Anki's 404 on mangatl's port counts as "up" by the probe's <500 rule.
    found += [dead for d in view.dashboards if d.clash]
    found += [c.arming for c in view.containers]
    return tuple(found)


def reason(view: LiveView) -> str:
    """Name what is down or clashing, for the collapsed row; empty when well."""
    down = [p.target for p in view.probes if p.up is False]
    down += [d.label for d in view.dashboards if d.probe.up is False]
    down += [
        f"{c.name} ({c.state or c.status})"
        for c in view.containers
        if c.arming is not Arming.ARMED
    ]
    parts = [f"down: {', '.join(down)}"] if down else []
    parts += [f"port clash: {d.label}: {d.clash}" for d in view.dashboards if d.clash]
    return "; ".join(parts)
