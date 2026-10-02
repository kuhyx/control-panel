"""The declared fleet: what *should* exist, loaded from ``manifest/``.

This exists because ``systemctl`` can only tell you about units that are
installed. ``phone-auto-sync.timer`` is referenced by an installer in
``~/src/phone-focus-mode`` but has no unit file on this machine, so enumerating
systemd finds nothing to report -- it is invisible, not unarmed. Comparing
systemd against a declared manifest is the only way that surfaces.

Three fields here cannot be computed and so must be declared:

``retired``
    systemd has no concept of one unit superseding another.
``login_oneshot`` / ``arming_lives_on``
    ``workout-locker.service`` is ``disabled`` yet armed, because it is
    ``WantedBy=graphical-session.target``. A naive "disabled means unarmed"
    rule false-positives on it.
``snapshot_dirs``
    orphaned ``disabled-*`` unit snapshots are just directories to systemd.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from control_panel._manifest_live import (
    IgnoredListener,
    ManifestError,
    ManifestLive,
    ManifestProbe,
    check_restartable,
    parse_ignored,
    parse_live,
    require,
)
from control_panel._types import Category, Scope

__all__ = ["IgnoredListener", "ManifestError", "ManifestLive", "ManifestProbe"]

MANIFEST_DIR = Path(__file__).resolve().parent.parent / "manifest"


@dataclass(frozen=True, slots=True)
class Retired:
    """A declaration that a unit has been superseded."""

    since: str
    superseded_by: str
    note: str = ""


@dataclass(frozen=True, slots=True)
class ManifestUnit:
    """One unit the fleet is declared to contain."""

    name: str
    scope: Scope
    kind: str
    retired: Retired | None = None
    login_oneshot: bool = False
    arming_lives_on: tuple[str, ...] = ()
    why_it_matters: str = ""
    restartable: bool = False
    on_demand: bool = False


@dataclass(frozen=True, slots=True)
class ManifestLog:
    """A declared, bounded-readable log for a subsystem."""

    id: str
    kind: str
    path: str = ""
    unit: str = ""
    scope: Scope = Scope.SYSTEM


@dataclass(frozen=True, slots=True)
class ManifestSource:
    """A file whose prose or reason column explains why a rule exists."""

    path: str
    label: str


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """One subsystem's declaration."""

    id: str
    title: str
    category: Category
    units: tuple[ManifestUnit, ...] = ()
    logs: tuple[ManifestLog, ...] = ()
    snapshot_dirs: tuple[str, ...] = ()
    docs: tuple[ManifestSource, ...] = ()
    audits: tuple[ManifestSource, ...] = ()
    facts: dict[str, Any] = field(default_factory=dict)
    live: ManifestLive = field(default_factory=ManifestLive)


def _parse_retired(raw: object, where: str) -> Retired | None:
    """Parse the optional ``retired`` block."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        msg = f"{where}: 'retired' must be an object"
        raise ManifestError(msg)
    return Retired(
        since=str(require(raw, "since", where)),
        superseded_by=str(require(raw, "superseded_by", where)),
        note=str(raw.get("note", "")),
    )


def _parse_unit(raw: object, where: str) -> ManifestUnit:
    """Parse one entry of a subsystem's ``units`` array."""
    if not isinstance(raw, dict):
        msg = f"{where}: each unit must be an object"
        raise ManifestError(msg)
    return ManifestUnit(
        name=str(require(raw, "name", where)),
        scope=Scope(require(raw, "scope", where)),
        kind=str(require(raw, "kind", where)),
        retired=_parse_retired(raw.get("retired"), where),
        login_oneshot=bool(raw.get("login_oneshot", False)),
        arming_lives_on=tuple(str(x) for x in raw.get("arming_lives_on", ())),
        why_it_matters=str(raw.get("why_it_matters", "")),
        restartable=bool(raw.get("restartable", False)),
        on_demand=bool(raw.get("on_demand", False)),
    )


def _parse_sources(raw: object, where: str) -> tuple[ManifestSource, ...]:
    """Parse a `docs` or `audits` array of {path, label} objects."""
    if not isinstance(raw, list):
        msg = f"{where}: rationale sources must be an array"
        raise ManifestError(msg)
    return tuple(
        ManifestSource(
            path=require(item, "path", where), label=require(item, "label", where)
        )
        for item in raw
        if isinstance(item, dict)
    )


def _parse_entry(raw: dict[str, Any], where: str) -> ManifestEntry:
    """Parse one ``manifest/subsystems/<id>.json`` document."""
    entry = _parse_fields(raw, where)
    check_restartable(
        entry.category,
        tuple((u.name, u.scope, u.restartable) for u in entry.units),
        entry.live.containers,
        where,
    )
    return entry


def _parse_fields(raw: dict[str, Any], where: str) -> ManifestEntry:
    """Parse every field of one subsystem, before cross-field checks."""
    return ManifestEntry(
        id=str(require(raw, "id", where)),
        title=str(require(raw, "title", where)),
        category=Category(require(raw, "category", where)),
        units=tuple(_parse_unit(u, where) for u in raw.get("units", ())),
        logs=tuple(
            ManifestLog(
                id=str(require(lg, "id", where)),
                kind=str(require(lg, "kind", where)),
                path=str(lg.get("path", "")),
                unit=str(lg.get("unit", "")),
                scope=Scope(lg.get("scope", Scope.SYSTEM)),
            )
            for lg in raw.get("logs", ())
        ),
        snapshot_dirs=tuple(str(d) for d in raw.get("snapshot_dirs", ())),
        docs=_parse_sources(raw.get("docs", []), where),
        audits=_parse_sources(raw.get("audits", []), where),
        facts=dict(raw.get("facts", {})),
        live=parse_live(raw, where),
    )


def _read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object, converting every failure into ManifestError."""
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"{path}: unreadable manifest ({exc})"
        raise ManifestError(msg) from exc
    if not isinstance(parsed, dict):
        msg = f"{path}: manifest must be a JSON object"
        raise ManifestError(msg)
    return parsed


def load_manifest(directory: Path | None = None) -> tuple[ManifestEntry, ...]:
    """Load every subsystem declaration, ordered by ``manifest/fleet.json``.

    Subsystems present on disk but absent from the order list are appended
    alphabetically rather than dropped -- a forgotten order entry must not
    silently hide a subsystem from the dashboard.
    """
    base = directory or MANIFEST_DIR
    fleet = _read_json(base / "fleet.json")
    order = [str(x) for x in fleet.get("order", ())]
    entries: dict[str, ManifestEntry] = {}
    for path in sorted((base / "subsystems").glob("*.json")):
        entry = _parse_entry(_read_json(path), str(path))
        if entry.id in entries:
            msg = f"{path}: duplicate subsystem id {entry.id!r}"
            raise ManifestError(msg)
        entries[entry.id] = entry
    if not entries:
        msg = f"{base / 'subsystems'}: no subsystem manifests found"
        raise ManifestError(msg)
    ordered = [entries.pop(name) for name in order if name in entries]
    ordered.extend(entries[name] for name in sorted(entries))
    return tuple(ordered)


def load_ignored_listeners(
    directory: Path | None = None,
) -> tuple[IgnoredListener, ...]:
    """Load the ports ``fleet.json`` deliberately leaves out of "unknown"."""
    base = directory or MANIFEST_DIR
    path = base / "fleet.json"
    return parse_ignored(_read_json(path).get("ignored_listeners"), str(path))
