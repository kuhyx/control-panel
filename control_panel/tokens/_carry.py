"""Carry-cost attribution: what each chunk of context cost while it stayed.

A chunk -- a tool result, an injected hook context, an attachment -- costs
its *creation* (the next call writes it to the prompt cache) plus its
*carry*: its tokens x every later API call of that session (until a
compaction drops it) x the cache-read price. Both are computed per chunk by
the ingester (``calls`` and ``marks`` tables); this panel only groups them.
Carry is part of the spend, not on top of it: it is the share of later
calls' cache-read bill that this chunk is responsible for.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25  # rows each table shows by default (t.<table>.limit=0: all)
MAX_FAMILIES = 1000
CONTEXT_READS = frozenset(
    {"Read:memory", "Read:rules", "Read:claude-md", "Read:skill", "Read:claude"}
)
WEB = frozenset({"WebFetch", "WebSearch"})
CAPTION = (
    "Carry cost = creation (the chunk's tokens x the cache-write price of the "
    "call that first sends it) + its tokens x every later API call of the same "
    "session until a compaction x the cache-read price. It is the share of "
    "later calls' cache-read bill the chunk caused, so it is part of the spend, "
    "not added to it. Token counts are estimates (4 chars/token; images "
    "~2.6k each)."
)

_FAMILIES = (
    "SELECT family, COUNT(*), SUM(result_tokens), SUM(create_usd),"
    " SUM(carry_usd), AVG(carry_calls) FROM calls WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY family ORDER BY SUM(create_usd + carry_usd) DESC LIMIT ?"
)
_TARGETS = (
    "SELECT name, family, target, COUNT(*), SUM(result_tokens), SUM(images),"
    " SUM(create_usd), SUM(carry_usd) FROM calls WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " AND name != 'Bash' GROUP BY name, family, target"
)
_MARKS = (
    "SELECT kind, name, detail, SUM(count), SUM(tokens), SUM(create_usd),"
    " SUM(carry_usd) FROM marks WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " AND tokens > 0 GROUP BY kind, name, detail"
)
_DAILY = (
    "SELECT day, 'calls', SUM(create_usd + carry_usd) FROM calls WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY day UNION ALL"
    " SELECT day, 'marks', SUM(create_usd + carry_usd) FROM marks WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY day"
)
_SPEND = (
    "SELECT COALESCE(SUM(usd), 0) FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
)


def _row(label: str, detail: str, nums: tuple[Any, ...]) -> dict[str, Any]:
    """One table row: count, tokens, creation, carry and their sum."""
    count, tokens, create, carry = nums
    return {
        "label": label,
        "detail": detail,
        "count": count,
        "tokens": tokens or 0,
        "create_usd": create or 0.0,
        "carry_usd": carry or 0.0,
        "total_usd": (create or 0.0) + (carry or 0.0),
    }


def _top(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The most expensive rows first (the table layer shows :data:`TOP`)."""
    return sorted(rows, key=lambda r: -r["total_usd"])


def _calls(conn: sqlite3.Connection, filters: Filters) -> dict[str, list[Any]]:
    """Non-Bash calls bucketed: MCP, skills, context reads, web, images, re-reads."""
    buckets: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for name, family, target, count, tokens, images, create, carry in conn.execute(
        _TARGETS, filters.params()
    ):
        row = _row(family, target, (count, tokens, create, carry))
        if family.startswith("mcp:"):
            buckets["mcp"].append(row)
        elif family == "skill":
            buckets["skills"].append(row)
        elif family in CONTEXT_READS:
            buckets["context_reads"].append(row)
        elif name in WEB:
            buckets["web"].append(row)
        if images:
            buckets["images"].append(
                _row(name, target, (images, tokens, create, carry))
            )
        if name == "Read" and count > 1:
            buckets["rereads"].append(row)
    return {name: _top(rows) for name, rows in buckets.items()}


def _marks(conn: sqlite3.Connection, filters: Filters) -> dict[str, list[Any]]:
    """Context marks bucketed: hook injections, attachments, pasted images."""
    buckets: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for kind, name, detail, count, tokens, create, carry in conn.execute(
        _MARKS, filters.params()
    ):
        row = _row(name, detail, (count, tokens, create, carry))
        if kind.startswith("hook_"):
            buckets["hooks"].append({**row, "label": f"{name} ({kind[5:]})"})
        elif kind == "image":
            buckets["pasted_images"].append(row)
        else:
            buckets["attachments"].append(row)
    return {name: _top(rows) for name, rows in buckets.items()}


def _daily(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Per day: tool-result carry vs every other context chunk's carry."""
    days: defaultdict[str, dict[str, float]] = defaultdict(
        lambda: {"calls": 0.0, "marks": 0.0}
    )
    for day, source, usd in conn.execute(_DAILY, filters.params() * 2):
        days[day][source] = usd
    return [
        {"day": day, "results_usd": v["calls"], "context_usd": v["marks"]}
        for day, v in sorted(days.items())
    ]


TABLES = (
    "families",
    "mcp",
    "skills",
    "context_reads",
    "web",
    "images",
    "rereads",
    "hooks",
    "attachments",
    "pasted_images",
)


@panel("carry", "Carry cost", order=60, tables={t: {"limit": str(TOP)} for t in TABLES})
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Carry attribution by command family, tool, hook, attachment and path."""
    families = [
        {
            **_row(family, "", (count, tokens, create, carry)),
            "carried_calls": round(avg or 0.0, 1),
        }
        for family, count, tokens, create, carry, avg in conn.execute(
            _FAMILIES, (*filters.params(), MAX_FAMILIES)
        )
    ]
    calls, marks = _calls(conn, filters), _marks(conn, filters)
    daily = _daily(conn, filters)
    total = sum(d["results_usd"] + d["context_usd"] for d in daily)
    names = ("mcp", "skills", "context_reads", "web", "images", "rereads")
    return {
        "caption": CAPTION,
        "totals": {
            "carry_total_usd": total,
            "spend_usd": conn.execute(_SPEND, filters.params()).fetchone()[0],
        },
        "daily": daily,
        "families": families,
        **{name: calls.get(name, []) for name in names},
        **{name: marks.get(name, []) for name in ("hooks", "attachments")},
        "pasted_images": marks.get("pasted_images", []),
    }
