"""Deliberate disarms: a guard its owner switched off on purpose, with a reason.

home-guard's ``scripts/disarm.sh`` masks its units and writes
``~/.local/share/home_guard/DISARMED`` ("disabled 2026-09-12 until the phone
app is standalone, multi-photo and zone-editable"). Without reading that
marker the dashboard reported a decision as a fault -- two BAD units holding
the tray icon red. With it, the units read DISARMED and the reason is shown.

A marker is only honoured where the manifest declares one, so a stray file
cannot quiet an arbitrary subsystem.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from control_panel import _sysroot
from control_panel._types import Arming

if TYPE_CHECKING:
    from control_panel._types import UnitRecord

# Shown in the collapsed row; the marker's own text follows it.
_MAX_REASON = 300
_KEEP = frozenset({Arming.ARMED, Arming.RETIRED})


def reason(marker: str) -> str | None:
    """The marker's text if the declared marker file exists, else None."""
    if not marker:
        return None
    path = (
        _sysroot.user_path(marker[2:])
        if marker.startswith("~/")
        else _sysroot.sysroot_path(marker)
    )
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return text.strip()[:_MAX_REASON] or "no reason recorded"


def apply(records: tuple[UnitRecord, ...], why: str) -> tuple[UnitRecord, ...]:
    """Re-label every not-armed unit as DISARMED, carrying the reason."""
    return tuple(
        record
        if record.arming in _KEEP
        else replace(
            record,
            arming=Arming.DISARMED,
            arming_reason=(*record.arming_reason, f"deliberately disarmed: {why}"),
        )
        for record in records
    )
