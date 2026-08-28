"""The declared fleet: what *should* exist, loaded from ``manifest/``.

This exists because ``systemctl`` can only tell you about units that are
installed. ``phone-auto-sync.timer`` is referenced by an installer in
``~/phone-focus-mode`` but has no unit file on this machine, so enumerating
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

from control_panel._types import Category, Scope

MANIFEST_DIR = Path(__file__).resolve().parent.parent / "manifest"


class ManifestError(RuntimeError):
    """Raised when the manifest is missing or structurally invalid.

    Fatal by design: a dashboard running against a half-read manifest would
    under-report exactly the missing units it exists to find.
    """


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


@dataclass(frozen=True, slots=True)
class ManifestProbe:
    """A declared liveness probe for a subsystem."""

    kind: str
    target: str


@dataclass(frozen=True, slots=True)
class ManifestLog:
    """A declared, bounded-readable log for a subsystem."""

    id: str
    kind: str
    path: str = ""
    unit: str = ""
    scope: Scope = Scope.SYSTEM


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """One subsystem's declaration."""

    id: str
    title: str
    category: Category
    units: tuple[ManifestUnit, ...] = ()
    probes: tuple[ManifestProbe, ...] = ()
    logs: tuple[ManifestLog, ...] = ()
    snapshot_dirs: tuple[str, ...] = ()
    facts: dict[str, Any] = field(default_factory=dict)


def _require(mapping: dict[str, Any], key: str, where: str) -> str:
    """Fetch a required key as a string, naming the file that lacked it.

    Every required field in the manifest is a string or a string-backed enum,
    so coercing here keeps the parse sites free of ``Any`` and lets mypy check
    them properly.
    """
    if key not in mapping:
        msg = f"{where}: missing required key {key!r}"
        raise ManifestError(msg)
    return str(mapping[key])


def _parse_retired(raw: object, where: str) -> Retired | None:
    """Parse the optional ``retired`` block."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        msg = f"{where}: 'retired' must be an object"
        raise ManifestError(msg)
    return Retired(
        since=str(_require(raw, "since", where)),
        superseded_by=str(_require(raw, "superseded_by", where)),
        note=str(raw.get("note", "")),
    )


def _parse_unit(raw: object, where: str) -> ManifestUnit:
    """Parse one entry of a subsystem's ``units`` array."""
    if not isinstance(raw, dict):
        msg = f"{where}: each unit must be an object"
        raise ManifestError(msg)
    return ManifestUnit(
        name=str(_require(raw, "name", where)),
        scope=Scope(_require(raw, "scope", where)),
        kind=str(_require(raw, "kind", where)),
        retired=_parse_retired(raw.get("retired"), where),
        login_oneshot=bool(raw.get("login_oneshot", False)),
        arming_lives_on=tuple(str(x) for x in raw.get("arming_lives_on", ())),
        why_it_matters=str(raw.get("why_it_matters", "")),
    )


def _parse_entry(raw: dict[str, Any], where: str) -> ManifestEntry:
    """Parse one ``manifest/subsystems/<id>.json`` document."""
    return ManifestEntry(
        id=str(_require(raw, "id", where)),
        title=str(_require(raw, "title", where)),
        category=Category(_require(raw, "category", where)),
        units=tuple(_parse_unit(u, where) for u in raw.get("units", ())),
        probes=tuple(
            ManifestProbe(
                kind=str(_require(p, "kind", where)),
                target=str(_require(p, "target", where)),
            )
            for p in raw.get("probes", ())
        ),
        logs=tuple(
            ManifestLog(
                id=str(_require(lg, "id", where)),
                kind=str(_require(lg, "kind", where)),
                path=str(lg.get("path", "")),
                unit=str(lg.get("unit", "")),
                scope=Scope(lg.get("scope", Scope.SYSTEM)),
            )
            for lg in raw.get("logs", ())
        ),
        snapshot_dirs=tuple(str(d) for d in raw.get("snapshot_dirs", ())),
        facts=dict(raw.get("facts", {})),
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
