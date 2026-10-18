"""Output tokens: thinking / text / tool calls, share of spend, longest replies.

The billed output total per call is exact (usage); its split is the
ingester's estimate (``turn_detail.out_*``): visible text and tool-call
blocks by length (4 chars/token), the billed rest is thinking, whose text
the transcript does not keep. Output dollars use the per-model list price
(:mod:`_token_classes_prices`).
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens._db import ratio
from control_panel.tokens._registry import panel
from control_panel.tokens._token_classes_prices import BOOK

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
MAX_LONGEST = 1000  # replies kept for the "longest" table
CAPTION = (
    "Output tokens are exact (billed usage); the thinking / text / tool-call "
    "split is an estimate: text and tool-call blocks by length (4 chars per "
    "token), the billed rest is thinking (its text is not in the transcript). "
    "Output $ = output tokens x the model's list output price; share = that / "
    "all spend in range. Longest replies: the 1000 calls with most output."
)

_SPLIT = (
    "SELECT day, SUM(out_think), SUM(out_text), SUM(out_tool) FROM turn_detail"
    " WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY day"
)
_TURNS = (
    "SELECT day, model, SUM(output), SUM(usd) FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " GROUP BY day, model"
)
_LONGEST = (
    "SELECT ts, key, model, output, usd FROM turns WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " ORDER BY output DESC LIMIT ?"
)
_LONGEST_SPLIT = (
    "SELECT key, ts, out_think, out_text, out_tool FROM turn_detail WHERE"
    " ts BETWEEN ? AND ? AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?) AND (? = -1 OR is_sub = ?)"
    " ORDER BY out_think + out_text + out_tool DESC LIMIT ?"
)


def _daily(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Per day: the split, output tokens and dollars, spend and share."""
    days: defaultdict[str, defaultdict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for day, model, output, usd in conn.execute(_TURNS, filters.params()):
        price = BOOK.price(model)
        days[day]["output"] += output
        days[day]["output_usd"] += price.usd(output, price.output)
        days[day]["spend_usd"] += usd
    for day, think, text, tool in conn.execute(_SPLIT, filters.params()):
        days[day].update(think=think, text=text, tool=tool)
    return [
        {
            "day": day,
            "think": int(row["think"]),
            "text": int(row["text"]),
            "tool": int(row["tool"]),
            "output": int(row["output"]),
            "output_usd": row["output_usd"],
            "spend_usd": row["spend_usd"],
            "output_share": ratio(row["output_usd"], row["spend_usd"]),
        }
        for day, row in sorted(days.items())
    ]


def _longest(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """The replies with the most output, with their split where recorded."""
    params = (*filters.params(), MAX_LONGEST)
    split = {
        (key, ts): (think, text, tool)
        for key, ts, think, text, tool in conn.execute(_LONGEST_SPLIT, params)
    }
    rows = []
    for ts, key, model, output, usd in conn.execute(_LONGEST, params):
        price = BOOK.price(model)
        think, text, tool = split.get((key, ts), (None, None, None))
        rows.append(
            {
                "ts": ts,
                "key": key,
                "model": model,
                "output": output,
                "output_usd": price.usd(output, price.output),
                "usd": usd,
                "think": think,
                "text": text,
                "tool": tool,
            }
        )
    return rows


@panel("output", "Output", order=80, tables={"longest": {"limit": str(TOP)}})
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Output split per day, output share of spend, longest replies."""
    daily = _daily(conn, filters)
    totals = {
        name: sum(d[name] for d in daily)
        for name in ("think", "text", "tool", "output", "output_usd", "spend_usd")
    }
    totals["output_share"] = ratio(totals["output_usd"], totals["spend_usd"])
    return {
        "caption": CAPTION,
        "totals": totals,
        "daily": daily,
        "longest": _longest(conn, filters),
    }
