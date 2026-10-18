"""What the agent-routing hook decided, for the Subagents panel.

``agent_model_pretool.sh`` (PreToolUse:Agent) rewrites a spawn's model and
says so in ``additionalContext``, so its ``hook_context`` marks count the
rewrites and its ``hook_run`` marks count the spawns it saw -- both stored,
so every filter applies. Its A/B arm assignments go to
``~/.claude/logs/agent-ab.jsonl``, read live when present (only the date
range applies: the log has no cwd/model/scope).
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from typing import TYPE_CHECKING, Any

from control_panel import _sysroot

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

AB_LOG = ".claude/logs/agent-ab.jsonl"
HOOK = "%agent_model_pretool%"
GAP = (
    "~/.claude/logs/agent-ab.jsonl (the routing hook's A/B arm log) does not "
    "exist yet; only the hook's stored marks are shown."
)

_MARKS = (
    "SELECT kind, SUM(count) FROM marks WHERE kind IN ('hook_run', 'hook_context')"
    " AND detail LIKE ? AND"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " GROUP BY kind"
)


def _stamp(entry: object) -> float | None:
    """The entry's ISO timestamp as unix time, ``None`` if it has none."""
    when = entry.get("ts") if isinstance(entry, dict) else None
    if not isinstance(when, str):
        return None
    try:
        return datetime.fromisoformat(when).timestamp()
    except ValueError:
        return None


def _ab_rows(filters: Filters) -> list[dict[str, Any]] | None:
    """A/B assignments in range by arm/class/type; ``None`` with no log."""
    path = _sysroot.user_path(AB_LOG)
    if not path.is_file():
        return None
    counts: Counter[tuple[str, str, str]] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        stamp = _stamp(entry)
        if stamp is None or not filters.since <= stamp <= filters.until:
            continue
        counts[
            str(entry.get("arm", "")),
            str(entry.get("class", "")),
            str(entry.get("subagent_type", "")),
        ] += 1
    return [
        {"arm": arm, "class": cls, "subagent_type": kind, "count": n}
        for (arm, cls, kind), n in counts.most_common()
    ]


def routing(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Hook runs, model rewrites, and the A/B log (or the gap)."""
    kinds = dict(conn.execute(_MARKS, (HOOK, *filters.params())).fetchall())
    ab = _ab_rows(filters)
    return {
        "hook_runs": kinds.get("hook_run", 0),
        "rewrites": kinds.get("hook_context", 0),
        "ab": ab or [],
        "gap": GAP if ab is None else "",
    }
