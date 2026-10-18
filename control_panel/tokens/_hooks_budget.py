"""The hook budget gate's last benchmark, read live from disk.

``~/.claude/scripts/hook_budget.py`` times every configured hook against a
per-event budget; ``~/.claude/hooks/hook_budget_guard.sh`` keeps its last
text report in ``~/.claude/state/hook_budget_result.txt`` (there is no hook
timing log under ``~/.claude/logs``). It is a point-in-time synthetic run,
so the dashboard's date / cwd / model / scope filters cannot apply to it.
"""

from __future__ import annotations

import re
from typing import Any

from control_panel import _sysroot

RESULT = ".claude/state/hook_budget_result.txt"
# "   0.06s    1.5s  ok    Stop              python3 /home/.../evidence..."
_LINE = re.compile(
    r"^\s*(?P<time>\d+(?:\.\d+)?)s\s+(?P<budget>\d+(?:\.\d+)?)s\s+"
    r"(?P<status>\S+)\s+(?P<event>\S+)\s+(?P<command>.+?)\s*$"
)
CAPTION = (
    "Last run of the hook budget gate (hook_budget.py, re-run when "
    "settings.json changes or weekly): each configured hook timed once on a "
    "synthetic input against its event's budget. A snapshot, not history: "
    "the date, cwd, model and scope filters do not apply. Commands are cut "
    "at ~40 characters by the gate itself."
)


def _row(match: re.Match[str]) -> dict[str, Any]:
    """One budget row: time, budget, how far over, event and command."""
    time_s, budget_s = float(match["time"]), float(match["budget"])
    return {
        "event": match["event"],
        "command": match["command"],
        "status": match["status"],
        "time_s": time_s,
        "budget_s": budget_s,
        "over_s": max(0.0, time_s - budget_s),
    }


def read() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Budget rows (slowest first) and what the file was (path, mtime, found)."""
    path = _sysroot.user_path(RESULT)
    info: dict[str, Any] = {
        "path": str(path),
        "found": False,
        "mtime": None,
        "over": 0,
        "caption": CAPTION,
    }
    try:
        text = path.read_text(encoding="utf-8")
        info["mtime"] = path.stat().st_mtime
    except OSError:
        return [], info
    rows = [_row(m) for m in map(_LINE.match, text.splitlines()) if m]
    rows.sort(key=lambda r: (-r["over_s"], -r["time_s"]))
    info["found"] = True
    info["over"] = sum(1 for r in rows if r["over_s"] > 0)
    return rows, info
