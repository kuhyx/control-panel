"""Manifest declarations for running things: dashboards, containers, restarts.

Split from :mod:`control_panel._manifest` for the same reason as
``_live_types``: servers brought declarations with no systemd counterpart. It
also owns :class:`ManifestError` and ``require`` so that both manifest modules
raise the same error without importing each other.

The one rule enforced here rather than by convention is **who may be
restarted**. ``restartable`` is accepted only on a ``server`` subsystem, and on
a unit only in the *user* scope. An enforcement unit marked restartable is a
load error, not a warning: a restart button on a guard is a way to switch it
off for a few seconds, which is the exact thing this dashboard must not offer.
System units are refused because restarting one needs root, and a button that
can only fail (or pops a polkit dialog on the live display) is worse than none.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SERVER_CATEGORY = "server"
USER_SCOPE = "user"


class ManifestError(RuntimeError):
    """Raised when the manifest is missing or structurally invalid.

    Fatal by design: a dashboard running against a half-read manifest would
    under-report exactly the missing units it exists to find.
    """


def require(mapping: dict[str, Any], key: str, where: str) -> str:
    """Fetch a required key as a string, naming the file that lacked it."""
    if key not in mapping:
        msg = f"{where}: missing required key {key!r}"
        raise ManifestError(msg)
    return str(mapping[key])


@dataclass(frozen=True, slots=True)
class ManifestProbe:
    """A declared liveness probe for a subsystem."""

    kind: str
    target: str


@dataclass(frozen=True, slots=True)
class ManifestDashboard:
    """A web UI a subsystem exposes.

    ``on_demand`` marks a UI that only exists while someone runs it by hand
    (book-guard-desktop), so a closed port is expected and is not probed.
    """

    label: str
    url: str
    on_demand: bool = False


@dataclass(frozen=True, slots=True)
class ManifestContainer:
    """A Docker container the subsystem runs on."""

    name: str
    restartable: bool = False


@dataclass(frozen=True, slots=True)
class ManifestLive:
    """Everything a subsystem declares about what should be *running*.

    One nested block rather than four more fields on ``ManifestEntry``, which
    is held to pylint's ten-attribute limit like every class here.
    """

    probes: tuple[ManifestProbe, ...] = ()
    dashboards: tuple[ManifestDashboard, ...] = ()
    containers: tuple[ManifestContainer, ...] = ()
    important: bool = True


@dataclass(frozen=True, slots=True)
class IgnoredListener:
    """A listening port deliberately left out of "unknown listeners"."""

    port: int
    why: str


def _objects(raw: object, key: str, where: str) -> list[dict[str, Any]]:
    """Return a list of objects, refusing anything else."""
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(x, dict) for x in raw):
        msg = f"{where}: {key!r} must be an array of objects"
        raise ManifestError(msg)
    return raw


def parse_live(raw: dict[str, Any], where: str) -> ManifestLive:
    """Parse the running-state fields of one subsystem document."""
    return ManifestLive(
        probes=tuple(
            ManifestProbe(
                kind=require(item, "kind", where), target=require(item, "target", where)
            )
            for item in _objects(raw.get("probes"), "probes", where)
        ),
        dashboards=parse_dashboards(raw.get("dashboards"), where),
        containers=parse_containers(raw.get("containers"), where),
        important=bool(raw.get("important", True)),
    )


def parse_dashboards(raw: object, where: str) -> tuple[ManifestDashboard, ...]:
    """Parse a subsystem's ``dashboards`` array."""
    return tuple(
        ManifestDashboard(
            label=require(item, "label", where),
            url=require(item, "url", where),
            on_demand=bool(item.get("on_demand", False)),
        )
        for item in _objects(raw, "dashboards", where)
    )


def parse_containers(raw: object, where: str) -> tuple[ManifestContainer, ...]:
    """Parse a subsystem's ``containers`` array."""
    return tuple(
        ManifestContainer(
            name=require(item, "name", where),
            restartable=bool(item.get("restartable", False)),
        )
        for item in _objects(raw, "containers", where)
    )


def check_restartable(
    category: str,
    units: tuple[tuple[str, str, bool], ...],
    containers: tuple[ManifestContainer, ...],
    where: str,
) -> None:
    """Refuse a restart permission anywhere it could weaken a guard.

    ``units`` is ``(name, scope, restartable)`` triples so this module need not
    import the unit dataclass from ``_manifest``.
    """
    flagged = [name for name, _, restartable in units if restartable]
    flagged += [c.name for c in containers if c.restartable]
    if flagged and category != SERVER_CATEGORY:
        msg = (
            f"{where}: {', '.join(flagged)} marked restartable in a "
            f"{category!r} subsystem; only 'server' subsystems may be restarted"
        )
        raise ManifestError(msg)
    system = [
        name
        for name, scope, restartable in units
        if restartable and scope != USER_SCOPE
    ]
    if system:
        msg = (
            f"{where}: {', '.join(system)} marked restartable but is not a user "
            "unit; restarting a system unit needs root"
        )
        raise ManifestError(msg)


def parse_ignored(raw: object, where: str) -> tuple[IgnoredListener, ...]:
    """Parse ``fleet.json``'s ``ignored_listeners`` array."""
    return tuple(
        IgnoredListener(
            port=int(require(item, "port", where)), why=require(item, "why", where)
        )
        for item in _objects(raw, "ignored_listeners", where)
    )
