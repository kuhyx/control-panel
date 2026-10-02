"""Collect the running half of each subsystem: dashboards, probes, containers.

Kept apart from :mod:`control_panel._aggregate` so the arming roll-up there
stays about systemd, and this module owns the one new rule: **what a failed
probe means.** On a ``server`` subsystem nothing answering *is* the outage, so
it is BAD. On an enforcement subsystem the web UI is a convenience beside the
real mechanism, so a dead one is only DEGRADED.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from control_panel import _docker, _probe
from control_panel._live_types import ContainerRecord, DashboardRecord, ProbeRecord
from control_panel._types import Arming, Category

if TYPE_CHECKING:
    from control_panel._manifest import ManifestEntry
    from control_panel._runner import CommandRunner


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


def collect(
    runner: CommandRunner, entries: tuple[ManifestEntry, ...]
) -> dict[str, LiveView]:
    """Probe everything once, concurrently, and read docker once."""
    results = _probe.run_all(_targets(entries))
    rows = (
        _docker.list_containers(runner)
        if any(e.live.containers for e in entries)
        else {}
    )
    containers = _docker.collect(entries, rows)
    views: dict[str, LiveView] = {}
    for entry in entries:
        views[entry.id] = LiveView(
            dashboards=tuple(
                DashboardRecord(
                    label=d.label,
                    url=d.url,
                    probe=_SKIPPED if d.on_demand else results["http", d.url],
                    on_demand=d.on_demand,
                )
                for d in entry.live.dashboards
            ),
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
    found += [c.arming for c in view.containers]
    return tuple(found)


def reason(view: LiveView) -> str:
    """Name what is down, for the collapsed row; empty when all is well."""
    down = [p.target for p in view.probes if p.up is False]
    down += [d.label for d in view.dashboards if d.probe.up is False]
    down += [
        f"{c.name} ({c.state or c.status})"
        for c in view.containers
        if c.arming is not Arming.ARMED
    ]
    return f"down: {', '.join(down)}" if down else ""
