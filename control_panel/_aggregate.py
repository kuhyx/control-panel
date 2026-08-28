"""Assemble the whole ``GET /api/status`` payload from collected units."""

from __future__ import annotations

from datetime import UTC, datetime
import socket
import time
from typing import TYPE_CHECKING

from control_panel import _anomalies, _collect, _manifest, _tail
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

    subsystems: list[SubsystemStatus] = []
    for entry in entries:
        records = units[entry.id]
        state = worst_arming(tuple(record.arming for record in records))
        subsystems.append(
            SubsystemStatus(
                id=entry.id,
                title=entry.title,
                category=entry.category,
                state=state,
                reason=_reason_for(state, records),
                source="systemd",
                read_at=_now(),
                units=records,
                facts=dict(entry.facts),
                logs=_log_refs(entry),
            )
        )

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
    )


def _reason_for(state: Arming, records: tuple[UnitRecord, ...]) -> str:
    """Summarise why a subsystem is in its state, for the collapsed row."""
    if not records:
        return "no systemd units; enforced by another mechanism"
    if state is Arming.ARMED:
        return f"all {len(records)} declared unit(s) armed"
    names = ", ".join(r.name for r in records if r.arming is state)
    return f"{state}: {names}"
