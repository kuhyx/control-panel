"""Session stats: how sessions are shaped -- cost, length, interruptions.

A session is a ``main_key`` (its subagents' calls count towards it unless
the scope filter drops them). Every number is over the turns inside the
filters; prompts (typed user turns) and interruptions are counted for the
sessions those turns belong to.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens._db import ratio
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    from collections.abc import Iterable
    import sqlite3

    from control_panel.tokens._db import Filters

SLOT_S = 600  # concurrency window: sessions with a call in the same 10 min
MAX_POSITION = 200
# (label, upper bound exclusive); the last bucket is open-ended.
COST_BUCKETS = (
    ("<$0.50", 0.5),
    ("$0.50-1", 1),
    ("$1-2", 2),
    ("$2-5", 5),
    ("$5-10", 10),
    ("$10-20", 20),
    ("$20-50", 50),
    ("$50-100", 100),
    ("$100+", float("inf")),
)
POSITION_BUCKETS = (
    ("1", 2),
    ("2-5", 6),
    ("6-10", 11),
    ("11-25", 26),
    ("26-50", 51),
    ("51-100", 101),
    ("101-200", 201),
)
PROMPT_BUCKETS = (
    ("0", 1),
    ("1", 2),
    ("2", 3),
    ("3-5", 6),
    ("6-10", 11),
    ("11-20", 21),
    ("21-50", 51),
    ("51+", float("inf")),
)
INTERRUPT_BUCKETS = (("0", 1), ("1", 2), ("2", 3), ("3-5", 6), ("6+", float("inf")))
CAPTION = (
    "A session = one main transcript plus its subagents (as far as the scope "
    "filter keeps them). Call position: the n-th API call of its own "
    "transcript (a subagent counts from 1), numbered before the filters, so a "
    "model filter does not renumber. Prompts = typed user turns. Concurrent = "
    "most sessions with a call in the same 10-minute window that day."
)

_TURNS = (
    "SELECT main_key, ts, day, usd FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " ORDER BY ts, main_key"
)
_POSITION = (
    "SELECT pos, COUNT(*), AVG(usd) FROM (SELECT ts, cwd, model, is_sub, usd,"
    " ROW_NUMBER() OVER (PARTITION BY key ORDER BY ts) AS pos FROM turns)"
    " WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " AND pos <= ? GROUP BY pos"
)
_INTERRUPTS = (
    "SELECT main_key, SUM(count) FROM marks WHERE kind = 'interrupt' AND"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY main_key"
)
_PROMPTS = "SELECT key, COUNT(*) FROM prompts GROUP BY key"


def bucket_of(value: float, buckets: tuple[tuple[str, float], ...]) -> str:
    """The label of the first bucket whose upper bound exceeds ``value``."""
    return next(label for label, upper in buckets if value < upper)


def histogram(
    values: Iterable[float], buckets: tuple[tuple[str, float], ...]
) -> list[dict[str, Any]]:
    """Sessions per bucket, every bucket listed (empty ones as 0)."""
    counts = Counter(bucket_of(v, buckets) for v in values)
    return [{"bucket": label, "sessions": counts[label]} for label, _ in buckets]


def _position(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Mean USD of the n-th call of a transcript, in position bins."""
    calls: Counter[str] = Counter()
    usd: defaultdict[str, float] = defaultdict(float)
    for pos, count, mean in conn.execute(_POSITION, (*filters.params(), MAX_POSITION)):
        label = bucket_of(pos, POSITION_BUCKETS)
        calls[label] += count
        usd[label] += mean * count
    return [
        {"bucket": b, "calls": calls[b], "mean_usd": ratio(usd[b], calls[b])}
        for b, _ in POSITION_BUCKETS
    ]


def _daily(turns: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    """Per day: sessions started, and the most active in one 10-minute slot."""
    first_day: dict[str, str] = {}
    slots: defaultdict[int, set[str]] = defaultdict(set)
    slot_day: dict[int, str] = {}
    for main, ts, day, _ in turns:
        first_day.setdefault(main, day)
        slot = int(ts // SLOT_S)
        slots[slot].add(main)
        slot_day.setdefault(slot, day)
    started = Counter(first_day.values())
    peak: defaultdict[str, int] = defaultdict(int)
    for slot, mains in slots.items():
        day = slot_day[slot]
        peak[day] = max(peak[day], len(mains))
    return [
        {"day": day, "sessions": started[day], "max_concurrent": peak[day]}
        for day in sorted(peak)
    ]


@panel(
    "session_stats",
    "Session stats",
    order=76,
    tables={"daily": {"limit": "0"}, "position": {"limit": "0"}},
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Cost, length, interruption and concurrency distributions of sessions."""
    turns = conn.execute(_TURNS, filters.params()).fetchall()
    cost: defaultdict[str, float] = defaultdict(float)
    for main, _, _, usd in turns:
        cost[main] += usd
    prompts = dict(conn.execute(_PROMPTS).fetchall())
    interrupts = dict(conn.execute(_INTERRUPTS, filters.params()).fetchall())
    total = sum(interrupts.get(k, 0) for k in cost)
    return {
        "caption": CAPTION,
        "totals": {
            "sessions": len(cost),
            "usd": sum(cost.values()),
            "usd_per_session": ratio(sum(cost.values()), len(cost)),
            "interrupts": total,
        },
        "cost_hist": histogram(cost.values(), COST_BUCKETS),
        "position": _position(conn, filters),
        "prompts_hist": histogram((prompts.get(k, 0) for k in cost), PROMPT_BUCKETS),
        "interrupts_hist": histogram(
            (interrupts.get(k, 0) for k in cost), INTERRUPT_BUCKETS
        ),
        "daily": _daily(turns),
    }
