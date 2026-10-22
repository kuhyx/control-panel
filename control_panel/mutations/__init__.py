"""The only package in control_panel that may change anything.

Pre-commit hooks state that boundary rather than leaving it to discipline:
``no-writes-outside-mutations`` keeps every other module a reader, and
``never-change-unit-state`` applies here too -- no mutation may start, stop,
enable, disable or mask a unit, because arming is not one of the approved knobs.
The single unit operation allowed is a *restart* of an allowlisted server
(:mod:`._restart`), and ``restart-only-in-restart-module`` keeps it there.

Approved by kuhy on 2026-10-22 for the sessions tab: :mod:`._session_resume`
opens a terminal through ``systemd-run --user --collect`` -- a *transient*
unit wrapping a terminal window, never a declared one, so it arms and disarms
nothing -- and :mod:`._session_mark` writes the dashboard's own
``~/.claude/session-status.json``. :mod:`._session_delete` *moves*
transcripts to ``~/.claude/projects-trash/<day>/`` (never unlinks; restore is
a move back). None of the three touches a guard.

Each mutation is a thin argv-builder. **None of them implements a comparator.**
"Is this stricter?" is answered by the scripts that already guard these files,
which is what makes the dashboard incapable of permitting something they would
refuse.
"""

from __future__ import annotations

from control_panel.mutations._types import MutationResult, to_payload

__all__ = ["MutationResult", "to_payload"]
