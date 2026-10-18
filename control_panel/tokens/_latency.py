"""Latency: how long the model, the tools and the user each take.

- *Model latency* (``turn_detail.latency_s``): time from the record before a
  reply to the reply's first record -- roughly time to first token, plus any
  harness overhead; 0 (no previous record) is left out.
- *Tool time* (``calls``): the tool_result record's time minus the tool_use
  record's, so it includes any wait on a permission prompt; results stamped
  before their call are dropped.
- *Think time*: from a reply's last API call to the user's next prompt in
  the same main session (subagents have no user); negative gaps (prompts
  queued while the reply ran) are dropped, idle breaks are kept.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens._context_growth_stats import bucket, percentiles
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
QS = (0.5, 0.9, 0.99)
THINK_EDGES = (0, 10, 30, 60, 300, 900, 3600, 14400)
THINK_LABELS = ("<10s", "10-30s", "30s-1m", "1-5m", "5-15m", "15m-1h", "1-4h", "4h+")
CAPTION = (
    "Model latency = time from the previous transcript record to the reply's "
    "first record (about time to first token plus harness overhead; calls with "
    "no previous record are left out). Tool time = tool result time - tool call "
    "time, so it includes waiting on a permission prompt. Think time = the gap "
    "from a reply's last API call to the next user prompt of the same main "
    "session; it includes idle breaks. Percentiles are nearest-rank."
)

_LATENCY = (
    "SELECT day, model, latency_s FROM turn_detail WHERE latency_s > 0 AND"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
)
_TOOLS = (
    "SELECT name, end_ts - ts FROM calls WHERE end_ts >= ts AND"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
)
_REPLIES = (
    "SELECT key, prompt_idx, MAX(ts) FROM turns WHERE is_sub = 0 AND"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY key, prompt_idx"
)
_PROMPTS = "SELECT key, idx, ts FROM prompts"


def _grouped(
    pairs: list[tuple[str, float]], label: str, qs: tuple[float, ...]
) -> list[dict[str, Any]]:
    """Rows of ``{label, calls, total_s, p..}`` per group."""
    groups: defaultdict[str, list[float]] = defaultdict(list)
    for name, value in pairs:
        groups[name].append(value)
    return [
        {label: name, "calls": len(v), "total_s": sum(v), **percentiles(v, qs)}
        for name, v in groups.items()
    ]


def _think(conn: sqlite3.Connection, filters: Filters) -> list[float]:
    """Seconds from each reply's last call to the next prompt (main only)."""
    prompts = {(key, idx): ts for key, idx, ts in conn.execute(_PROMPTS)}
    gaps = []
    for key, idx, last in conn.execute(_REPLIES, filters.params()):
        nxt = prompts.get((key, idx + 1))
        if nxt is not None and nxt >= last:
            gaps.append(nxt - last)
    return gaps


@panel(
    "latency",
    "Latency",
    order=78,
    tables={"tools": {"limit": str(TOP)}, "models": {"limit": str(TOP)}},
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Model latency per day and model, tool time per tool, user think time."""
    latency = conn.execute(_LATENCY, filters.params()).fetchall()
    daily = _grouped([(day, s) for day, _, s in latency], "day", QS)
    models = _grouped([(model, s) for _, model, s in latency], "model", QS)
    tool_times = conn.execute(_TOOLS, filters.params()).fetchall()
    tools = _grouped(tool_times, "name", (0.5, 0.95))
    gaps = _think(conn, filters)
    counts = [0] * len(THINK_LABELS)
    for gap in gaps:
        counts[bucket(gap, THINK_EDGES)] += 1
    return {
        "caption": CAPTION,
        "daily": sorted(daily, key=lambda r: r["day"]),
        "models": sorted(models, key=lambda r: -r["calls"]),
        "tools": sorted(tools, key=lambda r: -r["total_s"]),
        "think": {"prompts": len(gaps), **percentiles(gaps, (0.5, 0.9))},
        "think_histogram": [
            {"bucket": label, "prompts": counts[i]}
            for i, label in enumerate(THINK_LABELS)
        ],
    }
