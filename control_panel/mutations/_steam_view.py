"""Show the Steam exceptions. Read-only, and the panel says why.

This is the one knob that is deliberately *not* a knob. Adding an exception
here would appear to work and then silently not: the enforcer loads ``Config``
once at start and only reloads ``State`` on its 3-second tick, and it re-applies
``chattr +i`` to ``config.json`` every tick as well. A dashboard edit would be
reverted by the next iteration, or worse, ignored while looking accepted.

Offering a control that does nothing is worse than offering none, so the panel
shows the current exceptions, shows the audit trail, and states the reason it
cannot add to them.
"""

from __future__ import annotations

import json
from typing import Any

from control_panel import _sysroot, _tail

CONFIG_DIR = "~/.config/steam_backlog_enforcer"
APPROVED = "approved_exceptions.json"
AUDIT = "exception_audit.log"
AUDIT_LINES = 50

WHY_READ_ONLY = (
    "The enforcer loads config.json once at startup and re-applies chattr +i to "
    "it on every 3-second tick, so an exception added here would be silently "
    "reverted. Use `steam-backlog-enforcer add-exception <app_id> --reason ...`, "
    "which the daemon's own audit path understands."
)


def _read_approved() -> tuple[list[dict[str, Any]], str | None]:
    """Read the approved-exception list, reporting why if it cannot."""
    path = _sysroot.user_path(f"{CONFIG_DIR.removeprefix('~/')}/{APPROVED}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], "no exceptions have ever been approved"
    except (OSError, json.JSONDecodeError) as exc:
        # Several of this daemon's state files are root-owned 0600. Saying so
        # is the honest answer; escalating to sudo to read them would quietly
        # make this dashboard something other than an observer.
        return [], f"{path.name} could not be read: {exc}"
    if not isinstance(raw, list):
        return [], f"{path.name} is not a list"
    return [item for item in raw if isinstance(item, dict)], None


def view() -> dict[str, Any]:
    """Return the exceptions, the audit tail, and why this is read-only."""
    approved, detail = _read_approved()
    audit = _tail.tail(f"{CONFIG_DIR}/{AUDIT}", AUDIT_LINES)
    return {
        "approved": approved,
        "unreadable": detail,
        "audit": list(audit.lines),
        "audit_error": audit.error,
        "read_only": True,
        "why_read_only": WHY_READ_ONLY,
    }
