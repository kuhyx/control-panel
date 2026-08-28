"""Render the arming table on a terminal, with no HTTP server involved.

This is the Phase 0 gate: if `control-panel doctor` cannot tell you that
``phone-auto-sync.timer`` was never installed and ``kuhytrack-budget.timer`` is
disabled, no amount of frontend will fix it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from control_panel._types import Arming

if TYPE_CHECKING:
    from control_panel._manifest import ManifestEntry
    from control_panel._types import UnitRecord

# Rendered without colour when stdout is not a tty; a status table that is
# unreadable in a pipe is a status table nobody greps.
_COLOURS = {
    Arming.ARMED: "\033[32m",
    Arming.UNARMED: "\033[33m",
    Arming.DEGRADED: "\033[33m",
    Arming.BAD: "\033[31m",
    Arming.NOT_INSTALLED: "\033[31m",
    Arming.RETIRED: "\033[90m",
    Arming.UNKNOWN: "\033[35m",
}
_RESET = "\033[0m"
_NAME_WIDTH = 44
_STATE_WIDTH = 13


def _paint(state: Arming, text: str, *, colour: bool) -> str:
    """Wrap ``text`` in the colour for ``state`` when colour is enabled."""
    if not colour:
        return text
    return f"{_COLOURS[state]}{text}{_RESET}"


def _unit_line(record: UnitRecord, *, colour: bool) -> str:
    """Render one unit as an aligned table row."""
    name = f"  {record.name} ({record.scope})"
    state = _paint(record.arming, f"{record.arming:<{_STATE_WIDTH}}", colour=colour)
    return f"{name:<{_NAME_WIDTH}} {state} {'; '.join(record.arming_reason)}"


def render(
    entries: tuple[ManifestEntry, ...],
    units: dict[str, tuple[UnitRecord, ...]],
    *,
    colour: bool = True,
) -> str:
    """Render the whole fleet as a plain-text table."""
    lines: list[str] = []
    tally: dict[Arming, int] = {}
    for entry in entries:
        records = units.get(entry.id, ())
        lines.append(f"\n{entry.title}  [{entry.category}]")
        if not records:
            lines.append("  (no systemd units -- enforced by another mechanism)")
        for record in records:
            tally[record.arming] = tally.get(record.arming, 0) + 1
            lines.append(_unit_line(record, colour=colour))
    lines.append("")
    summary = "  ".join(
        _paint(state, f"{state}={tally[state]}", colour=colour)
        for state in Arming
        if state in tally
    )
    lines.append(summary)
    return "\n".join(lines)


def problems(units: dict[str, tuple[UnitRecord, ...]]) -> tuple[UnitRecord, ...]:
    """Return every unit that is neither armed nor deliberately retired."""
    healthy = {Arming.ARMED, Arming.RETIRED}
    return tuple(
        record
        for records in units.values()
        for record in records
        if record.arming not in healthy
    )
