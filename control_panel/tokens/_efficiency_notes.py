"""USD per completed todo note, read live from token_audit's notes.json.

Each note's USD is the lifetime list-price spend of the sessions linked to it,
split equally across a session's notes. The date range applies to the weekly
series (by done date); cwd, model and scope do not apply.
"""

from __future__ import annotations

import json
from typing import Any

from control_panel import _sysroot
from control_panel.tokens import _db

NOTES = ".claude/token-report/notes.json"
CAPTION = (
    "USD per completed todo note: lifetime spend of sessions linked to notes "
    "done or abandoned that week / notes done that week. Links come from "
    "note_claim.sh, todo-images prompts, a fuzzy first-prompt match and handoff "
    "chains (token_audit). The date range picks weeks by done date; cwd, model "
    "and scope do not apply."
)
Row = dict[str, Any]


def read() -> list[Row]:
    """Every linked note from notes.json, most expensive first."""
    try:
        data = json.loads(_sysroot.user_path(NOTES).read_text(encoding="utf-8"))
    except OSError, ValueError:
        return []
    notes = data.get("notes") if isinstance(data, dict) else None
    rows = [
        {
            "id": n.get("id"),
            "title": n.get("title"),
            "status": n.get("status"),
            "priority": n.get("priority"),
            "done": _db.day_of(n["done_at"]) if n.get("done_at") else None,
            "done_at": n.get("done_at"),
            "sessions": len(n.get("sessions") or []),
            "usd": n.get("usd") or 0.0,
            "tokens": n.get("tokens") or 0,
        }
        for n in (notes if isinstance(notes, list) else [])
        if isinstance(n, dict)
    ]
    return sorted(rows, key=lambda r: -r["usd"])


def weekly(rows: list[Row], since: float, until: float) -> list[Row]:
    """Per week of done date: done, abandoned, their USD and USD per note."""
    weeks: dict[str, Row] = {}
    for row in rows:
        stamp = row["done_at"]
        status = row["status"]
        if status not in {"done", "abandoned"} or not since <= stamp <= until:
            continue
        week = weeks.setdefault(
            _db.monday(_db.day_of(stamp)), {"done": 0, "abandoned": 0, "usd": 0.0}
        )
        week[status] += 1
        week["usd"] += row["usd"]
    return [
        weeks[name]
        | {
            "week": name,
            "usd_per_note": _db.ratio(weeks[name]["usd"], weeks[name]["done"]),
        }
        for name in sorted(weeks)
    ]
