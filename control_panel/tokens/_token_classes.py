"""Token classes and the prompt cache: what each class of token cost, per day.

Each API call bills five classes: input, cache write (5-minute or 1-hour
TTL), cache read and output. ``turns`` stores the per-call totals and
``turn_detail`` the 1h/5m write split; older turns without a split show as
*unsplit* and are priced as 5m writes (token_audit's rule: an underestimate).
Classes are priced per model with token_audit's list-price table
(:mod:`_token_classes_prices`), so their sum reconciles with ``turns.usd``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens import _token_classes_waste as tw
from control_panel.tokens._db import ratio
from control_panel.tokens._registry import panel
from control_panel.tokens._token_classes_prices import BOOK

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
CLASSES = ("input", "cw_5m", "cw_1h", "unsplit", "cache_read", "output")
CAPTION = (
    "Tokens per class from each call's usage; dollars = tokens x token_audit's "
    "list price for the call's model (5m write = 1.25x input, 1h = 2x; writes "
    "with no 1h/5m split are 'unsplit' and priced as 5m). Hit ratio = cache "
    "read / (cache read + cache write + input). Waste = a cache write whose key "
    "made no further call within 1 h (the longest TTL), so its prefix was never "
    "re-read; writes in the range's last hour are pending, not waste; a floor, "
    "since 5m writes re-used after 5-60 min are not counted. Cold start = a "
    "call with no cache read but a cache write (its whole cost). Compaction "
    "cost is an estimate: the summary call is not in the transcript, so it is "
    "preTokens x cache-read price + postTokens x output price."
)

_TURNS = (
    "SELECT day, model, SUM(input), SUM(cache_write), SUM(cache_read),"
    " SUM(output), SUM(usd) FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY day, model"
)
_SPLIT = (
    "SELECT day, model, SUM(cw_5m), SUM(cw_1h) FROM turn_detail WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY day, model"
)


def _priced(model: str, tokens: dict[str, int]) -> dict[str, float]:
    """Dollars per class for one model's tokens."""
    price = BOOK.price(model)
    rates = {
        "input": price.input,
        "cw_5m": price.write_5m,
        "cw_1h": price.write_1h,
        "unsplit": price.write_5m,
        "cache_read": price.cache_read,
        "output": price.output,
    }
    return {f"{c}_usd": price.usd(tokens[c], rates[c]) for c in CLASSES}


def _tokens(split: tuple[int, int], usage: tuple[int, ...]) -> dict[str, int]:
    """Tokens per class from a usage sum and its 5m/1h write split."""
    five, hour = split
    inp, write, read, out = usage
    return {
        "input": inp,
        "cw_5m": five,
        "cw_1h": hour,
        "unsplit": max(0, write - five - hour),
        "cache_read": read,
        "output": out,
    }


def _classes(
    conn: sqlite3.Connection, filters: Filters
) -> dict[str, defaultdict[str, float]]:
    """Per day: tokens and dollars of every class, plus the recorded spend."""
    split = {
        (day, model): (five, hour)
        for day, model, five, hour in conn.execute(_SPLIT, filters.params())
    }
    days: dict[str, defaultdict[str, float]] = {}
    for day, model, inp, write, read, out, usd in conn.execute(
        _TURNS, filters.params()
    ):
        tokens = _tokens(split.get((day, model), (0, 0)), (inp, write, read, out))
        row = days.setdefault(day, defaultdict(float))
        for name, value in (*tokens.items(), *_priced(model, tokens).items()):
            row[name] += value
        row["spend_usd"] += usd
    return days


def _day_row(day: str, row: dict[str, float], waste: tw.Waste) -> dict[str, Any]:
    """One chart/table row: every class, its dollars, hit ratio, waste."""
    writes = row["cw_5m"] + row["cw_1h"] + row["unsplit"]
    lost = waste.of_day(day)
    return {
        "day": day,
        **{c: int(row[c]) for c in CLASSES},
        **{f"{c}_usd": row[f"{c}_usd"] for c in CLASSES},
        "usd": sum(row[f"{c}_usd"] for c in CLASSES),
        "spend_usd": row["spend_usd"],
        "hit_ratio": ratio(
            row["cache_read"], row["cache_read"] + writes + row["input"]
        ),
        "waste_usd": lost.wasted_usd,
        "cold_starts": lost.cold_starts,
    }


@panel(
    "token_classes",
    "Token classes & cache",
    order=66,
    tables={"waste": {"limit": str(TOP)}, "compactions": {"limit": str(TOP)}},
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Classes per day, cache hit ratio, waste, cold starts and compactions."""
    waste = tw.waste(conn, filters)
    days = _classes(conn, filters)
    daily = [_day_row(day, days[day], waste) for day in sorted(days)]
    events = tw.compactions(conn, filters)
    sums = {c: sum(d[c] for d in daily) for c in CLASSES}
    writes = sums["cw_5m"] + sums["cw_1h"] + sums["unsplit"]
    return {
        "caption": CAPTION,
        "prices_source": BOOK.source,
        "totals": {
            **sums,
            "usd": sum(d["usd"] for d in daily),
            "spend_usd": sum(d["spend_usd"] for d in daily),
            "hit_ratio": ratio(
                sums["cache_read"], sums["cache_read"] + writes + sums["input"]
            ),
            **waste.totals(),
            "compactions": sum(e["count"] for e in events),
            "compaction_usd": sum(e["est_usd"] for e in events),
        },
        "daily": daily,
        "waste": waste.rows(),
        "compactions": events,
    }
