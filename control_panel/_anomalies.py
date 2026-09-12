"""Cross-cutting findings that are no single subsystem's responsibility.

Two of these can only be found here, not by walking declared units:

* ``undeclared-bad-unit`` -- ``code-tunnel.service`` is broken but belongs to no
  subsystem, so a manifest walk never reaches it. Only a fleet-wide sweep of
  ``list-unit-files --state=bad`` finds it.
* ``orphaned-unit-snapshot`` -- a ``disabled-*`` directory of saved unit files
  is just a directory to systemd, and records that enforcement was once turned
  off by hand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from control_panel import _sysroot, _tail
from control_panel._types import Anomaly, Arming, Level, Scope

if TYPE_CHECKING:
    from pathlib import Path

    from control_panel._collect import SystemdView
    from control_panel._manifest import ManifestEntry
    from control_panel._types import SubsystemStatus

# Unit states that mean "this will not fire", mapped to how loudly to say so.
_UNIT_SEVERITY = {
    Arming.BAD: Level.DANGER,
    Arming.NOT_INSTALLED: Level.DANGER,
    Arming.UNARMED: Level.WARN,
    Arming.DEGRADED: Level.WARN,
    Arming.UNKNOWN: Level.WARN,
}


def _slug(name: str) -> str:
    """Turn a unit name into an anomaly-id fragment."""
    return name.replace(".", "-").replace("@", "-at-").replace("_", "-")


def _unit_anomalies(subsystems: tuple[SubsystemStatus, ...]) -> list[Anomaly]:
    """Raise one anomaly per declared unit that will not fire."""
    found: list[Anomaly] = []
    for subsystem in subsystems:
        for record in subsystem.units:
            severity = _UNIT_SEVERITY.get(record.arming)
            if severity is None:
                continue
            found.append(
                Anomaly(
                    id=f"{_slug(record.name)}-{record.arming.lower()}",
                    subsystem=subsystem.id,
                    severity=severity,
                    title=f"{record.name} is {record.arming}",
                    detail="; ".join(record.arming_reason),
                    evidence=(
                        f"scope={record.scope}",
                        f"UnitFileState={record.state.unit_file_state}",
                        f"preset={record.state.preset}",
                    ),
                )
            )
    return found


def _declared_units(entries: tuple[ManifestEntry, ...]) -> set[tuple[str, Scope]]:
    """Return every unit any subsystem declares."""
    return {(unit.name, unit.scope) for entry in entries for unit in entry.units}


def _undeclared_bad(
    entries: tuple[ManifestEntry, ...], view: SystemdView
) -> list[Anomaly]:
    """Report units systemd cannot parse that no subsystem claims."""
    declared = _declared_units(entries)
    found: list[Anomaly] = []
    for scope in Scope:
        for name in sorted(view.bad[scope]):
            if (name, scope) in declared:
                continue
            found.append(
                Anomaly(
                    id=f"undeclared-bad-{_slug(name)}",
                    subsystem="",
                    severity=Level.WARN,
                    title=f"{name} is a broken unit file and is undeclared",
                    detail=(
                        "systemd reports this unit as `bad`, and no subsystem "
                        "manifest claims it -- so nothing owns fixing or "
                        "removing it."
                    ),
                    evidence=(
                        f"scope={scope}",
                        "`systemctl list-unit-files --state=bad`",
                    ),
                )
            )
    return found


def _log_anomalies(subsystems: tuple[SubsystemStatus, ...]) -> list[Anomaly]:
    """Report logs that have grown without any logrotate policy."""
    found: list[Anomaly] = []
    for subsystem in subsystems:
        for ref in subsystem.logs:
            size = ref.bytes
            if ref.kind != "file" or size is None:
                continue
            # Two distinct faults, and conflating them hides the worse one.
            # No logrotate entry at all means the file grows forever. An entry
            # that exists while the file is still 57 MB means rotation is
            # configured and *not working*, which no size threshold alone
            # would tell you.
            if ref.rotated:
                if size < _tail.UNROTATED_DANGER_BYTES:
                    continue
                found.append(
                    Anomaly(
                        id=f"log-rotation-ineffective-{ref.id}",
                        subsystem=subsystem.id,
                        severity=Level.WARN,
                        title=(
                            f"{ref.path} is {size // (1024 * 1024)} MB despite "
                            f"having a logrotate entry"
                        ),
                        detail=(
                            "A logrotate config mentions this file, yet it has "
                            "grown past 32 MB -- the rotation is configured but "
                            "is not taking effect."
                        ),
                        evidence=(f"{size} bytes", f"mtime={ref.mtime}"),
                    )
                )
                continue
            if size >= _tail.UNROTATED_DANGER_BYTES:
                level = Level.DANGER
            elif size >= _tail.UNROTATED_WARN_BYTES:
                level = Level.WARN
            else:
                continue
            found.append(
                Anomaly(
                    id=f"log-unrotated-{ref.id}",
                    subsystem=subsystem.id,
                    severity=level,
                    title=f"{ref.path} is {size // (1024 * 1024)} MB and unrotated",
                    detail=(
                        "No file in /etc/logrotate.d mentions this log, so it "
                        "grows without bound."
                    ),
                    evidence=(f"{size} bytes", f"mtime={ref.mtime}"),
                )
            )
    return found


def _snapshot_anomalies(entries: tuple[ManifestEntry, ...]) -> list[Anomaly]:
    """Report saved-off directories of disabled units.

    These are the fingerprint of enforcement having been switched off by hand
    and never switched back -- invisible to systemd, which sees only a folder.
    """
    return [
        Anomaly(
            id=f"orphaned-unit-snapshot-{_slug(path.name)}",
            subsystem=entry.id,
            severity=Level.INFO,
            title=f"orphaned unit snapshot {path.name}",
            detail=(
                "A saved copy of disabled unit files. It records that "
                "enforcement was turned off by hand at some point; nothing "
                "removes it automatically."
            ),
            evidence=(str(path),),
        )
        for entry in entries
        for pattern in entry.snapshot_dirs
        for path in sorted(_expand(pattern))
    ]


def _expand(pattern: str) -> list[Path]:
    """Glob a manifest-declared directory pattern under the sysroot."""
    if pattern.startswith("~/"):
        base = _sysroot.user_path("")
        relative = pattern[2:]
    else:
        base = _sysroot.sysroot_path("/")
        relative = pattern.lstrip("/")
    try:
        return [path for path in base.glob(relative) if path.is_dir()]
    except OSError:
        return []


def detect(
    entries: tuple[ManifestEntry, ...],
    subsystems: tuple[SubsystemStatus, ...],
    view: SystemdView,
) -> tuple[Anomaly, ...]:
    """Run every anomaly rule, most severe first."""
    found = (
        _unit_anomalies(subsystems)
        + _undeclared_bad(entries, view)
        + _log_anomalies(subsystems)
        + _snapshot_anomalies(entries)
    )
    order = {Level.DANGER: 0, Level.WARN: 1, Level.INFO: 2}
    return tuple(sorted(found, key=lambda a: (order[a.severity], a.id)))
