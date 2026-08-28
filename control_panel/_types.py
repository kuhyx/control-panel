"""Frozen domain types for the fleet status snapshot.

Deliberately I/O-free: nothing here imports ``subprocess``, ``pathlib`` for
reading, or anything that touches the machine. That is what lets the arming
state machine in :mod:`control_panel._arming` be tested exhaustively as a pure
function, which is where most of the branch coverage in this package lives.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Arming(StrEnum):
    """Whether a unit will actually fire when its trigger comes around.

    ``RETIRED`` is *declared* in the manifest -- systemd has no concept of one
    unit superseding another, so it cannot be computed. Every other member is
    computed from systemd's own view.
    """

    ARMED = "ARMED"
    UNARMED = "UNARMED"
    DEGRADED = "DEGRADED"
    BAD = "BAD"
    NOT_INSTALLED = "NOT_INSTALLED"
    RETIRED = "RETIRED"
    UNKNOWN = "UNKNOWN"


# Worst-first severity order. A subsystem reports the worst state among its
# units, so this tuple is the tie-break for the whole dashboard.
ARMING_SEVERITY: tuple[Arming, ...] = (
    Arming.BAD,
    Arming.NOT_INSTALLED,
    Arming.UNARMED,
    Arming.DEGRADED,
    Arming.UNKNOWN,
    Arming.RETIRED,
    Arming.ARMED,
)


def worst_arming(states: tuple[Arming, ...]) -> Arming:
    """Return the state a subsystem should report, given its units' states.

    Retired units are excluded unless *every* unit is retired. A subsystem is
    not retired because it still carries the superseded units it migrated away
    from: hosts blocking keeps five retired guards alongside three live ones,
    and the curfew keeps the old midnight-shutdown pair. Ranking those above
    ARMED labelled both of those systems "RETIRED" on the dashboard while they
    were actively enforcing.
    """
    live = tuple(state for state in states if state is not Arming.RETIRED)
    if not live:
        return Arming.RETIRED if states else Arming.ARMED
    # The loop always returns: `live` is non-empty here and ARMING_SEVERITY
    # lists every Arming member, so there is no fallthrough to guard.
    return next(state for state in ARMING_SEVERITY if state in live)


class Scope(StrEnum):
    """Which systemd manager owns a unit."""

    SYSTEM = "system"
    USER = "user"


class Category(StrEnum):
    """Coarse grouping used to order and colour the dashboard."""

    ENFORCEMENT = "enforcement"
    SERVER = "server"
    MAINTENANCE = "maintenance"
    TELEMETRY = "telemetry"


class Level(StrEnum):
    """Severity of a signal or anomaly."""

    INFO = "info"
    WARN = "warn"
    DANGER = "danger"


@dataclass(frozen=True, slots=True)
class Signal:
    """A note attached to one subsystem, rendered as a chip in the UI."""

    level: Level
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class AdapterError:
    """A failure captured *into* a record rather than raised.

    One broken adapter must never blank the panel, so every collection failure
    becomes data. ``kind`` is one of ``timeout``, ``exec``, ``parse``,
    ``permission``.
    """

    kind: str
    message: str
    argv: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class UnitRecord:
    """One systemd unit as the dashboard sees it.

    ``installed=False`` is the load-bearing case: ``phone-auto-sync.timer`` is
    declared by an installer script but has no unit file on this machine, so it
    is invisible to ``systemctl`` entirely and can only be found by comparing
    against the manifest.
    """

    name: str
    scope: Scope
    arming: Arming
    expected: bool = True
    installed: bool = True
    unit_file_state: str | None = None
    preset: str | None = None
    active_state: str | None = None
    sub_state: str | None = None
    result: str | None = None
    next_elapse: str | None = None
    last_trigger: str | None = None
    exec_start: str | None = None
    exec_start_exists: bool | None = None
    declared_retired: bool = False
    login_oneshot: bool = False
    arming_reason: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProbeRecord:
    """The result of a liveness probe against a loopback endpoint.

    Unit state is not liveness: ``stunnel-dot.service`` is ``enabled`` with
    nothing listening on :853, and ``steam-backlog-enforcer.service`` is
    ``active`` with nothing on :8000 because it runs the daemon, not ``serve``.
    """

    kind: str
    target: str
    up: bool
    status: int | None = None
    latency_ms: float | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class LogRef:
    """A pointer to a bounded, readable log for one subsystem."""

    id: str
    kind: str
    path: str | None = None
    unit: str | None = None
    scope: Scope | None = None
    bytes: int | None = None
    rotated: bool | None = None
    mtime: str | None = None


@dataclass(frozen=True, slots=True)
class SubsystemStatus:
    """Everything the dashboard knows about one subsystem."""

    id: str
    title: str
    category: Category
    state: Arming
    reason: str = ""
    source: str = "systemd"
    read_at: str = ""
    duration_ms: int = 0
    error: AdapterError | None = None
    units: tuple[UnitRecord, ...] = ()
    probes: tuple[ProbeRecord, ...] = ()
    facts: dict[str, Any] = field(default_factory=dict)
    logs: tuple[LogRef, ...] = ()
    signals: tuple[Signal, ...] = ()


@dataclass(frozen=True, slots=True)
class Anomaly:
    """A cross-cutting finding that is no single adapter's responsibility."""

    id: str
    subsystem: str
    severity: Level
    title: str
    detail: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Collector:
    """Metadata about the collection run itself."""

    duration_ms: int
    degraded: bool
    journal_readable: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FleetStatus:
    """The whole ``GET /api/status`` payload."""

    schema_version: int
    generated_at: str
    host: str
    port: int
    collector: Collector
    rollup: dict[str, int]
    subsystems: tuple[SubsystemStatus, ...]
    anomalies: tuple[Anomaly, ...]


def to_payload(status: FleetStatus) -> dict[str, Any]:
    """Convert a :class:`FleetStatus` into a JSON-serialisable dict.

    ``asdict`` leaves ``StrEnum`` members as enum instances, but every enum
    here subclasses ``str``, so ``json.dumps`` emits them as plain strings
    without a custom encoder.
    """
    return asdict(status)
