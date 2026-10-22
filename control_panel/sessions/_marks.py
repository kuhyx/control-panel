"""Read manual session marks: ``{"<id>": {"mark": "done", "at": <epoch>}}``.

Reading only. The single writer is :mod:`control_panel.mutations._session_mark`,
because every write in this repo lives under ``mutations/``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

MARKS = ("done",)


def read_marks(path: Path) -> dict[str, dict[str, Any]]:
    """Return every well-formed mark; a missing or broken file is no marks.

    A corrupt marks file must not take the session list down with it: the
    worst case is that hand-marked sessions show as open again.
    """
    try:
        raw = json.loads(path.read_bytes())
    except OSError, ValueError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(sid): entry
        for sid, entry in raw.items()
        if isinstance(entry, dict) and entry.get("mark") in MARKS
    }
