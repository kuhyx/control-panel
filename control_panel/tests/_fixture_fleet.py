"""A small fleet that reproduces the real machine's anomalies in miniature."""

from __future__ import annotations

from dataclasses import replace

from control_panel import _systemctl
from control_panel._collect import SystemdView
from control_panel._manifest import (
    ManifestEntry,
    ManifestLog,
    ManifestUnit,
    Retired,
)
from control_panel._types import Category, Scope

_BASE_ENTRY = ManifestEntry(id="s", title="S", category=Category.ENFORCEMENT)
_BASE_UNIT = ManifestUnit(name="x", scope=Scope.USER, kind="service")


def entry(**changes: object) -> ManifestEntry:
    """Return the base subsystem with the given fields replaced.

    `dataclasses.replace` keeps this typed without a per-field signature, so
    adding a field to ManifestEntry does not mean editing every test helper.
    """
    return replace(_BASE_ENTRY, **changes)


def timer(name: str, scope: Scope = Scope.USER, **changes: object) -> ManifestUnit:
    """Return a declared timer."""
    return replace(_BASE_UNIT, name=name, scope=scope, kind="timer", **changes)


def service(name: str, scope: Scope = Scope.USER, **changes: object) -> ManifestUnit:
    """Return a declared service."""
    return replace(_BASE_UNIT, name=name, scope=scope, kind="service", **changes)


def view(
    *,
    user_files: dict[str, tuple[str, str]] | None = None,
    system_files: dict[str, tuple[str, str]] | None = None,
    user_timers: dict[str, int | None] | None = None,
    bad_user: frozenset[str] = frozenset(),
) -> SystemdView:
    def files(raw: dict[str, tuple[str, str]] | None) -> dict[str, _systemctl.UnitFile]:
        return {
            name: _systemctl.UnitFile(name=name, state=state, preset=preset)
            for name, (state, preset) in (raw or {}).items()
        }

    return SystemdView(
        unit_files={Scope.USER: files(user_files), Scope.SYSTEM: files(system_files)},
        timers={
            Scope.USER: {
                name: _systemctl.TimerRow(
                    unit=name, next_elapse=nxt, last_trigger=1, activates=None
                )
                for name, nxt in (user_timers or {}).items()
            },
            Scope.SYSTEM: {},
        },
        bad={Scope.USER: bad_user, Scope.SYSTEM: frozenset()},
    )


__all__ = ["ManifestLog", "Retired", "entry", "service", "timer", "view"]
