"""The only package in control_panel that may change anything.

Two pre-commit hooks state that boundary rather than leaving it to discipline:
``no-writes-outside-mutations`` keeps every other module a reader, and
``never-change-unit-state`` applies here too -- no mutation may start, stop,
enable, disable or mask a unit, because arming is not one of the approved knobs.

Each mutation is a thin argv-builder. **None of them implements a comparator.**
"Is this stricter?" is answered by the scripts that already guard these files,
which is what makes the dashboard incapable of permitting something they would
refuse.
"""

from __future__ import annotations

from control_panel.mutations._types import MutationResult, to_payload

__all__ = ["MutationResult", "to_payload"]
