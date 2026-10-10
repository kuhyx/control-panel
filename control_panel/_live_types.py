"""Frozen record types for what is *running*, as opposed to what is armed.

Split out of :mod:`control_panel._types` when the dashboard grew past
enforcement units to every server on the machine: a Docker container, a
dashboard URL and a liveness probe have no systemd unit file to diff against,
so they need their own records. Annotation-only imports keep this module and
``_types`` free of a runtime import cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from control_panel._types import Arming


@dataclass(frozen=True, slots=True)
class ProbeRecord:
    """The result of a liveness probe against a loopback endpoint.

    Unit state is not liveness: ``stunnel-dot.service`` is ``enabled`` with
    nothing listening on :853. ``up`` is ``None`` when the target was never
    probed -- a public URL, or a dashboard that only exists on demand.
    """

    kind: str
    target: str
    up: bool | None
    status: int | None = None
    latency_ms: float | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class DashboardRecord:
    """One clickable web UI belonging to a subsystem, with its probe result.

    ``stopped``: an on-demand UI whose units are all inactive and whose port
    nothing of its own holds -- render it as stopped, not as a dead link.
    ``clash``: a foreign unit or container holds the port (see _port_owner).
    """

    label: str
    url: str
    probe: ProbeRecord
    on_demand: bool = False
    stopped: bool = False
    clash: str | None = None


@dataclass(frozen=True, slots=True)
class ContainerRecord:
    """One declared Docker container, as ``docker ps -a`` reports it.

    ``arming`` reuses the unit vocabulary so a subsystem made of containers
    rolls up through the same ``worst_arming`` as one made of units.
    """

    name: str
    arming: Arming
    state: str = ""
    status: str = ""
    restartable: bool = False


@dataclass(frozen=True, slots=True)
class Listener:
    """A TCP listener that no manifest entry accounts for."""

    address: str
    port: int
    process: str = ""


@dataclass(frozen=True, slots=True)
class UndeclaredUnit:
    """A unit file in the user's systemd directory that no entry declares."""

    name: str
    scope: str
