"""Cache writes nobody re-read, cold starts and compactions (token classes).

Rules, stated in the panel caption too:

- *Waste*: a call's cache write counts as wasted when the same key (session
  or subagent) makes no further call within 1 h -- the longest cache TTL, so
  the written prefix can never have been read. A write with no next call
  within the last hour of the range is *pending* (the session may go on), not
  waste. 5m writes followed by a call 5-60 min later are not counted, so this
  is a floor.
- *Cold start*: a call with ``cache_read == 0`` and ``cache_write > 0``; its
  cost is the call's whole ``usd``.
- *Compaction*: ``marks`` kind ``compaction`` (tokens = preTokens, extra =
  postTokens). The summarising call is not in the transcript, so its cost is
  estimated as preTokens x cache-read price + postTokens x output price.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from control_panel.tokens._token_classes_prices import BOOK

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TTL_S = 3600.0

_CALLS = (
    "SELECT key, ts, day, model, cache_write, cache_read, usd FROM turns WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " ORDER BY key, ts"
)
_SPLIT = (
    "SELECT key, ts, cw_1h, cw_5m FROM turn_detail WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
)
_COMPACTIONS = (
    "SELECT ts, key, model, name, count, tokens, extra, duration_ms FROM marks"
    " WHERE kind = 'compaction' AND"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
)


@dataclass
class Bucket:
    """One key's wasted writes and cold starts."""

    wasted_calls: int = 0
    wasted_tokens: int = 0
    wasted_usd: float = 0.0
    cold_starts: int = 0
    cold_start_usd: float = 0.0


@dataclass
class Waste:
    """Waste and cold starts, in total, per key and per day."""

    keys: defaultdict[str, Bucket] = field(default_factory=lambda: defaultdict(Bucket))
    days: defaultdict[str, Bucket] = field(default_factory=lambda: defaultdict(Bucket))
    pending_tokens: int = 0

    def of_day(self, day: str) -> Bucket:
        """One day's waste and cold starts (empty when it had none)."""
        return self.days.get(day) or Bucket()

    def record(self, call: tuple[Any, ...], fate: str, split: tuple[int, int]) -> None:
        """Count one writing call: cold start, and pending or wasted write."""
        key, _, day, model, write, read, usd = call
        buckets = (self.keys[key], self.days[day])
        if read == 0:
            for bucket in buckets:
                bucket.cold_starts += 1
                bucket.cold_start_usd += usd
        if fate == "pending":
            self.pending_tokens += write
        elif fate == "wasted":
            cost = _write_usd(model, split, write)
            for bucket in buckets:
                bucket.wasted_calls += 1
                bucket.wasted_tokens += write
                bucket.wasted_usd += cost

    def rows(self) -> list[dict[str, Any]]:
        """Per key, most wasted dollars first."""
        rows = [{"key": key, **vars(k)} for key, k in self.keys.items()]
        return sorted(rows, key=lambda r: (-r["wasted_usd"], -r["cold_start_usd"]))

    def totals(self) -> dict[str, Any]:
        """Sums over every key."""
        keys = self.keys.values()
        return {
            "waste_tokens": sum(k.wasted_tokens for k in keys),
            "waste_usd": sum(k.wasted_usd for k in keys),
            "pending_tokens": self.pending_tokens,
            "cold_starts": sum(k.cold_starts for k in keys),
            "cold_start_usd": sum(k.cold_start_usd for k in keys),
        }


def _write_usd(model: str, split: tuple[int, int], cache_write: int) -> float:
    """A call's cache write in dollars: 1h, 5m and unsplit (priced as 5m)."""
    one_hour, five_min = split
    price = BOOK.price(model)
    unsplit = max(0, cache_write - one_hour - five_min)
    return price.usd(one_hour, price.write_1h) + price.usd(
        five_min + unsplit, price.write_5m
    )


def _fate(calls: list[Any], index: int, until: float) -> str:
    """``kept`` (re-read within 1 h), ``pending`` (range end) or ``wasted``."""
    key, ts = calls[index][0], calls[index][1]
    nxt = calls[index + 1] if index + 1 < len(calls) else None
    if nxt is not None and nxt[0] == key:
        return "kept" if nxt[1] - ts <= TTL_S else "wasted"
    return "pending" if ts > until - TTL_S else "wasted"


def waste(conn: sqlite3.Connection, filters: Filters) -> Waste:
    """Walk each key's calls in order; a write with no call within 1 h is waste."""
    splits = {
        (key, ts): (one_hour, five_min)
        for key, ts, one_hour, five_min in conn.execute(_SPLIT, filters.params())
    }
    calls = conn.execute(_CALLS, filters.params()).fetchall()
    out = Waste()
    for index, call in enumerate(calls):
        if call[4] > 0:
            fate = _fate(calls, index, filters.until)
            out.record(call, fate, splits.get((call[0], call[1]), (0, 0)))
    return out


def compactions(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Compaction events with their estimated summary-call cost, dearest first."""
    rows = []
    for ts, key, model, trigger, count, pre, post, ms in conn.execute(
        _COMPACTIONS, filters.params()
    ):
        price = BOOK.price(model)
        rows.append(
            {
                "ts": ts,
                "key": key,
                "model": model,
                "trigger": trigger,
                "count": count,
                "pre_tokens": pre,
                "post_tokens": post,
                "duration_s": (ms or 0) / 1000,
                "est_usd": price.usd(pre, price.cache_read)
                + price.usd(post, price.output),
            }
        )
    return sorted(rows, key=lambda r: -r["est_usd"])
