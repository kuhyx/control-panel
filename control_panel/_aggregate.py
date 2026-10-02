"""Assemble the whole ``GET /api/status`` payload from collected units."""

from __future__ import annotations

from datetime import UTC, datetime
import socket
import time
from typing import TYPE_CHECKING

from control_panel import _anomalies, _collect, _disarm, _live, _manifest, _tail
from control_panel._types import (
    Arming,
    Collector,
    FleetStatus,
    LogRef,
    Scope,
    SubsystemStatus,
    UnitRecord,
    worst_arming,
)

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner

SCHEMA_VERSION = 1


def _now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


def _log_refs(entry: _manifest.ManifestEntry) -> tuple[LogRef, ...]:
    """Describe each declared log without reading it.

    Size is stat-only: the largest log in this fleet is 57 MB, and the whole
    point of the bounded reader is that nothing ever loads one whole.
    """
    refs: list[LogRef] = []
    for declared in entry.logs:
        if declared.kind == "journal":
            refs.append(
                LogRef(
                    id=declared.id,
                    kind="journal",
                    unit=declared.unit,
                    scope=declared.scope,
                )
            )
            continue
        stat = _tail.describe(declared.path)
        refs.append(
            LogRef(
                id=declared.id,
                kind="file",
                path=declared.path,
                bytes=stat.size,
                rotated=stat.rotated,
                mtime=stat.mtime,
            )
        )
    return tuple(refs)


def build_status(runner: CommandRunner, port: int) -> FleetStatus:
    """Collect the fleet and project it into the API payload."""
    started = time.monotonic()
    entries = _manifest.load_manifest()
    view = _collect.read_systemd(runner)
    units = _collect.collect_units(runner, entries, view)
    live = _live.collect(runner, entries)

    subsystems = [
        _subsystem(entry, units[entry.id], live[entry.id]) for entry in entries
    ]

    found = _anomalies.detect(entries, subsystems, view)
    rollup: dict[str, int] = {}
    for subsystem in subsystems:
        for record in subsystem.units:
            rollup[record.arming] = rollup.get(record.arming, 0) + 1

    return FleetStatus(
        schema_version=SCHEMA_VERSION,
        generated_at=_now(),
        host=socket.gethostname(),
        port=port,
        collector=Collector(
            duration_ms=int((time.monotonic() - started) * 1000),
            degraded=any(not view.unit_files[scope] for scope in Scope),
            journal_readable=True,
        ),
        rollup=rollup,
        subsystems=tuple(subsystems),
        anomalies=found,
        live=live,
    )


def _subsystem(
    entry: _manifest.ManifestEntry,
    records: tuple[UnitRecord, ...],
    running: _live.LiveView,
) -> SubsystemStatus:
    """Roll one subsystem's units and running state into its status row."""
    why = _disarm.reason(entry.live.disarm_marker)
    if why is not None:
        records = _disarm.apply(records, why)
    state = worst_arming(
        tuple(record.arming for record in records)
        + _live.states(entry.category, running)
    )
    reason = _live.reason(running) or _reason_for(state, records, running)
    if why is not None and state is Arming.DISARMED:
        reason = f"disarmed on purpose: {why}"
    return SubsystemStatus(
        id=entry.id,
        title=entry.title,
        category=entry.category,
        state=state,
        reason=reason,
        source="systemd",
        read_at=_now(),
        units=records,
        facts=dict(entry.facts),
        logs=_log_refs(entry),
    )


def _reason_for(
    state: Arming, records: tuple[UnitRecord, ...], running: _live.LiveView
) -> str:
    """Summarise why a subsystem is in its state, for the collapsed row."""
    if not records and (running.containers or running.dashboards):
        return "no systemd units; every container and dashboard answers"
    if not records:
        return "no systemd units; enforced by another mechanism"
    if state is Arming.ARMED:
        return f"all {len(records)} declared unit(s) armed"
    names = ", ".join(r.name for r in records if r.arming is state)
    return f"{state}: {names}"
