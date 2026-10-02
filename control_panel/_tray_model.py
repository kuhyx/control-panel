"""What the i3 tray icon shows, decided here rather than in the tray script.

The tray runs under the system Python (PyGObject is not in any venv) and is
copied to ``~/.config/i3/scripts``, outside this package's tests. So it is
kept dumb: it fetches ``GET /api/tray`` and renders exactly what it is told.
Every decision -- colour, tooltip, menu order -- lives here, at 100% branch
coverage.

Colour rule (agreed 2026-10-02): **red** when an *important* subsystem is
BAD, NOT_INSTALLED or UNARMED; **amber** when anything else is not healthy;
**ok** otherwise. The tray adds a fourth, "unreachable", on its own when this
endpoint does not answer.
"""

from __future__ import annotations

from typing import Any

from control_panel._types import Arming

RED_STATES = frozenset({Arming.BAD, Arming.NOT_INSTALLED, Arming.UNARMED})
HEALTHY_STATES = frozenset({Arming.ARMED, Arming.RETIRED})
LEVEL_RED = "red"
LEVEL_AMBER = "amber"
LEVEL_OK = "ok"
_TOOLTIP_LIMIT = 8


def level_of(subsystem: dict[str, Any]) -> str:
    """One subsystem's colour, before ``important`` is considered."""
    state = subsystem["state"]
    if state in RED_STATES:
        return LEVEL_RED
    return LEVEL_OK if state in HEALTHY_STATES else LEVEL_AMBER


def overall(subsystems: list[dict[str, Any]]) -> str:
    """The icon's colour: red needs an important subsystem, amber does not."""
    levels = [(level_of(s), bool(s.get("important", True))) for s in subsystems]
    if any(level == LEVEL_RED and important for level, important in levels):
        return LEVEL_RED
    if any(level != LEVEL_OK for level, _ in levels):
        return LEVEL_AMBER
    return LEVEL_OK


def _tooltip(subsystems: list[dict[str, Any]]) -> str:
    """Name what is wrong, worst first, capped so the tooltip stays readable."""
    bad = [s for s in subsystems if level_of(s) != LEVEL_OK]
    if not bad:
        return f"All {len(subsystems)} subsystems healthy"
    bad.sort(key=lambda s: level_of(s) != LEVEL_RED)
    lines = [f"{s['title']}: {s['state']}" for s in bad[:_TOOLTIP_LIMIT]]
    if len(bad) > _TOOLTIP_LIMIT:
        lines.append(f"... and {len(bad) - _TOOLTIP_LIMIT} more")
    return "\n".join([f"{len(bad)} of {len(subsystems)} need attention", *lines])


def build(status: dict[str, Any], panel_url: str) -> dict[str, Any]:
    """Project the fleet status into the tray's whole view."""
    subsystems: list[dict[str, Any]] = list(status["subsystems"])
    return {
        "level": overall(subsystems),
        "tooltip": _tooltip(subsystems),
        "panel_url": panel_url,
        "items": [
            {
                "id": s["id"],
                "title": s["title"],
                "state": s["state"],
                "level": level_of(s),
                "panel_url": f"{panel_url}#/s/{s['id']}",
                "dashboards": [
                    {"label": d["label"], "url": d["url"]}
                    for d in s.get("dashboards", ())
                ],
            }
            for s in subsystems
        ],
    }
