"""Prompt habits: how the way a session is started relates to what it costs.

Sessions are the ``main_key`` values of the turns inside the filters, with
their cost there. Prompts come from the ``prompts`` table (typed user turns
only). The ingester stores at most 120 characters of each prompt, so every
longer prompt lands in the top length bucket.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens._db import home, ratio
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
STORED_CHARS = 120  # token_dashboard's PROMPT_CHARS: prompts are cut there
PREFIXES = ("LONG:", "OPUS:", "HERE:", "override", "SOLVE:")
LENGTH_BUCKETS = (
    ("no prompt", 1),
    ("1-20", 21),
    ("21-50", 51),
    ("51-100", 101),
    ("101-119", STORED_CHARS),
    ("120 (truncated)", STORED_CHARS + 1),
)
CAPTION = (
    "Length = characters of the session's opening prompt (its first typed "
    "prompt that is not a /slash command; whitespace collapsed). The store "
    "keeps only the first 120 characters of a prompt, so "
    "'120 (truncated)' means 120 or longer. Session cost = its calls inside the "
    "filters. Prefixes count typed prompts starting with the tag ('override' "
    "in any case); session $ = the cost of the sessions that used it. Started "
    "from ~ = sessions whose working directory was the home directory."
)

_SESSIONS = (
    "SELECT main_key, SUM(usd) FROM turns WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " GROUP BY main_key"
)
_PROMPTS = "SELECT key, idx, ts, text FROM prompts ORDER BY key, idx"
_CWDS = "SELECT key, cwd FROM session_summary"


def _bucket(length: int) -> str:
    """The length bucket of an opening prompt (0: the session had none)."""
    return next(label for label, upper in LENGTH_BUCKETS if length < upper)


def _prefix(text: str) -> str | None:
    """The habit tag a prompt starts with, if any."""
    stripped = text.lstrip()
    for tag in PREFIXES:
        head = stripped[: len(tag)]
        if head == tag or (tag == "override" and head.lower() == tag):
            return tag
    return None


def _lengths(
    cost: dict[str, float], opening: dict[str, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Per session (opening prompt, length, cost) and per length bucket."""
    sessions: list[dict[str, Any]] = [
        {
            "key": key,
            "prompt": opening.get(key, ""),
            "length": len(opening.get(key, "")),
            "usd": usd,
        }
        for key, usd in cost.items()
    ]
    sessions.sort(key=lambda r: -r["usd"])
    usd: defaultdict[str, list[float]] = defaultdict(list)
    for row in sessions:
        usd[_bucket(row["length"])].append(row["usd"])
    buckets = [
        {
            "bucket": label,
            "sessions": len(usd[label]),
            "total_usd": sum(usd[label]),
            "mean_usd": ratio(sum(usd[label]), len(usd[label])),
        }
        for label, _ in LENGTH_BUCKETS
    ]
    return sessions, buckets


def _prefixes(
    cost: dict[str, float], tagged: dict[str, list[str]]
) -> list[dict[str, Any]]:
    """Per tag: prompts, sessions using it, and those sessions' cost."""
    rows = []
    for tag in PREFIXES:
        keys = tagged.get(tag, [])
        unique = set(keys)
        rows.append(
            {
                "prefix": tag,
                "prompts": len(keys),
                "sessions": len(unique),
                "session_usd": sum(cost[k] for k in unique),
            }
        )
    return rows


def _home(conn: sqlite3.Connection, cost: dict[str, float]) -> dict[str, Any]:
    """Sessions started in the home directory: count and cost share."""
    cwds = dict(conn.execute(_CWDS).fetchall())
    mine = [k for k in cost if cwds.get(k) == home()]
    usd = sum(cost[k] for k in mine)
    return {
        "sessions": len(mine),
        "usd": usd,
        "usd_share": ratio(usd, sum(cost.values())),
        "session_share": ratio(len(mine), len(cost)),
    }


@panel(
    "prompt_habits",
    "Prompt habits",
    order=90,
    tables={
        "sessions": {"limit": str(TOP)},
        "length_buckets": {"limit": "0"},
        "prefixes": {"limit": "0"},
    },
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Prompt length vs cost, habit prefixes, sessions started from ~."""
    cost = dict(conn.execute(_SESSIONS, filters.params()).fetchall())
    opening: dict[str, str] = {}
    tagged: defaultdict[str, list[str]] = defaultdict(list)
    for key, _, ts, text in conn.execute(_PROMPTS):
        if key not in cost:
            continue
        if not (text or "/").startswith("/"):
            opening.setdefault(key, text)
        tag = _prefix(text or "")
        if tag is not None and filters.since <= ts <= filters.until:
            tagged[tag].append(key)
    sessions, buckets = _lengths(cost, opening)
    return {
        "caption": CAPTION,
        "sessions": sessions,
        "length_buckets": buckets,
        "prefixes": _prefixes(cost, tagged),
        "home": _home(conn, cost),
    }
