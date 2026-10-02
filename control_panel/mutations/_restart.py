"""Restart one declared server: the only unit-state change this package makes.

Agreed 2026-10-02 as a deliberate, narrow exception to "the dashboard never
changes unit state": a stuck signal-bot or gitea should be one click away, but
a guard must never be. The allowlist is the manifest, and the manifest loader
already refuses ``restartable`` on anything but a user unit or container in a
``server`` subsystem (:mod:`control_panel._manifest_live`). This module checks
the request against that allowlist again, so a hand-built POST naming
``workout-locker.service`` is refused here as well.

Restart only. Not start, stop, enable, disable or mask: a restart leaves the
unit exactly as armed as it was, so it cannot be used to switch anything off.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from control_panel import _manifest
from control_panel.mutations._types import MutationResult

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner

TIMEOUT = 60.0
UNIT = "unit"
CONTAINER = "container"


def _allowed(kind: str, name: str) -> bool:
    """Whether the manifest marks this unit or container restartable."""
    for entry in _manifest.load_manifest():
        if kind == UNIT and any(u.restartable and u.name == name for u in entry.units):
            return True
        if kind == CONTAINER and any(
            c.restartable and c.name == name for c in entry.live.containers
        ):
            return True
    return False


def _argv(kind: str, name: str) -> tuple[str, ...]:
    """The command for one restart. User units only: see the module docstring."""
    if kind == CONTAINER:
        return ("docker", "restart", name)
    return ("systemctl", "--user", "restart", name)


def apply(runner: CommandRunner, body: object) -> MutationResult:
    """Restart one allowlisted unit or container."""
    if not isinstance(body, dict):
        return MutationResult.failure("Expected a JSON object.")
    kind = str(body.get("kind", ""))
    name = str(body.get("name", ""))
    if kind not in {UNIT, CONTAINER} or not name:
        return MutationResult.failure(
            "Expected 'kind' ('unit' or 'container') and a 'name'."
        )
    if not _allowed(kind, name):
        return MutationResult.refusal(
            f"{name} is not restartable from the dashboard.",
            stderr="Only user units and containers marked restartable in a "
            "'server' manifest entry can be restarted here.",
        )
    argv = _argv(kind, name)
    result = runner.run(argv, timeout=TIMEOUT)
    if result.ok:
        return MutationResult.success(f"{name} restarted.", argv=argv)
    return MutationResult.failure(
        f"Restarting {name} failed.",
        stderr=(result.error or result.stderr.strip())[-4000:],
    )
