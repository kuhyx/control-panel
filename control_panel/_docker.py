"""Docker containers: the half of the server fleet systemd cannot see.

gitea, Home Assistant, open-webui, searxng, syncyomi, endurain, signal-api and
the Caddy fronts all run as containers, so ``systemctl`` reports nothing about
them -- the same invisibility the manifest exists to defeat for uninstalled
units. One ``docker ps -a`` per collection covers every container.

The user is in the ``docker`` group, so no sudo is involved. If ``docker`` is
missing or the daemon is down, every container is UNKNOWN rather than BAD:
"could not ask" is not "it is dead".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from control_panel._live_types import ContainerRecord
from control_panel._types import Arming

if TYPE_CHECKING:
    from control_panel._manifest import ManifestEntry
    from control_panel._runner import CommandRunner

# Named fields, not `{{json .}}`: the JSON form makes docker compute every
# field, sizes included, and took 5.2 s here against 14 ms for these four.
# The ID lets a listener's ``docker-<id>.scope`` cgroup be named (_port_owner).
PS_ARGV = (
    "docker",
    "ps",
    "-a",
    "--format",
    "{{.Names}}\t{{.State}}\t{{.Status}}\t{{.ID}}",
)
_FIELDS = 3
_DEAD_STATES = frozenset({"exited", "dead", "created", "paused", "removing"})


def read_containers(
    runner: CommandRunner,
) -> tuple[dict[str, tuple[str, str]], dict[str, str]] | None:
    """Map container name to ``(State, Status)`` and to its short ID.

    None if docker is unusable. A row without the ID column still counts; its
    container simply cannot be matched to a listener's cgroup.
    """
    result = runner.run(PS_ARGV)
    if not result.ok:
        return None
    rows: dict[str, tuple[str, str]] = {}
    ids: dict[str, str] = {}
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) in {_FIELDS, _FIELDS + 1}:
            rows[fields[0]] = (fields[1], fields[2])
            if len(fields) > _FIELDS:
                ids[fields[0]] = fields[_FIELDS]
    return rows, ids


def list_containers(runner: CommandRunner) -> dict[str, tuple[str, str]] | None:
    """Map container name to ``(State, Status)``, or None if docker is unusable."""
    read = read_containers(runner)
    return None if read is None else read[0]


def _arming(state: str, status: str) -> Arming:
    """Translate a container state into the unit vocabulary."""
    if state == "running":
        # Docker appends "(unhealthy)" to Status when a HEALTHCHECK fails.
        return Arming.DEGRADED if "unhealthy" in status else Arming.ARMED
    if state == "restarting":
        return Arming.DEGRADED
    return Arming.BAD if state in _DEAD_STATES else Arming.UNKNOWN


def collect(
    entries: tuple[ManifestEntry, ...], rows: dict[str, tuple[str, str]] | None
) -> dict[str, tuple[ContainerRecord, ...]]:
    """Evaluate every declared container against one ``docker ps`` listing."""
    out: dict[str, tuple[ContainerRecord, ...]] = {}
    for entry in entries:
        records: list[ContainerRecord] = []
        for declared in entry.live.containers:
            if rows is None:
                arming, state, status = Arming.UNKNOWN, "", "docker unavailable"
            elif declared.name not in rows:
                arming, state, status = Arming.NOT_INSTALLED, "", "no such container"
            else:
                state, status = rows[declared.name]
                arming = _arming(state, status)
            records.append(
                ContainerRecord(
                    name=declared.name,
                    arming=arming,
                    state=state,
                    status=status,
                    restartable=declared.restartable,
                )
            )
        out[entry.id] = tuple(records)
    return out
