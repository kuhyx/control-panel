"""Compact markdown rendering with a hard output cap.

This server exists to save tokens, so every answer is a small table, never
the raw payload, and is cut at ~4k tokens with a note saying so.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
import json
from pathlib import Path
from typing import Any

CAP_CHARS = 16_000  # ~4k tokens at 4 chars/token
CELL = 60
WHOLE_DOLLARS_FROM = 100
WHOLE_NUMBER_FROM = 10
HOME = str(Path.home())
Row = dict[str, Any]
Column = tuple[str, Callable[[Row], str]]


def cap(text: str) -> str:
    """Cut ``text`` to the cap on a line boundary, saying so."""
    if len(text) <= CAP_CHARS:
        return text
    cut = text.rfind("\n", 0, CAP_CHARS)
    kept = text[: cut if cut > 0 else CAP_CHARS]
    return (
        f"{kept}\n\n_truncated at ~4k tokens ({len(kept)} of {len(text)} chars):"
        " narrow with limit / filters / search._"
    )


def as_json(data: object) -> str:
    """Compact JSON, capped like everything else."""
    return cap(json.dumps(data, separators=(",", ":"), default=str))


def usd(value: object) -> str:
    """Dollars: cents under $100, whole dollars above."""
    if not isinstance(value, int | float):
        return "-"
    return f"${value:,.2f}" if abs(value) < WHOLE_DOLLARS_FROM else f"${value:,.0f}"


def num(value: object) -> str:
    """A number, short; ``-`` for nulls."""
    if isinstance(value, bool) or value is None:
        return "-" if value is None else str(value)
    if isinstance(value, float):
        return f"{value:,.3g}" if abs(value) < WHOLE_NUMBER_FROM else f"{value:,.0f}"
    if isinstance(value, int):
        return f"{value:,}"
    return cell(value)


def share(value: object) -> str:
    """A 0..1 fraction as a percentage."""
    return f"{value:.0%}" if isinstance(value, int | float) else "-"


def dur(seconds: object) -> str:
    """Seconds as ``1h05m`` / ``42m`` / ``7s``."""
    if not isinstance(seconds, int | float):
        return "-"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m" if minutes else f"{secs}s"


def day(ts: object) -> str:
    """Unix seconds as a local date."""
    if not isinstance(ts, int | float):
        return "-"
    return datetime.fromtimestamp(ts).astimezone().strftime("%Y-%m-%d")


def cell(value: object, width: int = CELL) -> str:
    """One table-safe line, ``~`` for $HOME, ellipsised at ``width``."""
    out = "-" if value is None else str(value)
    out = out.replace(HOME, "~").replace("|", "/").replace("\n", " ").strip()
    return out if len(out) <= width else out[: width - 1] + "…"


def auto(key: str, value: object) -> str:
    """Format a cell by its column name (what the API's units say)."""
    if "usd" in key:
        return usd(value)
    if key.endswith(("share", "rate")):
        return share(value)
    if key.endswith("_s"):
        return dur(value)
    if key == "ts" or key.endswith("_ts"):
        return day(value)
    return num(value)


def col(
    key: str, label: str = "", fmt: Callable[[object], str] | None = None
) -> Column:
    """A column reading ``row[key]`` through ``fmt`` (default: by name)."""
    return (label or key, lambda row: (fmt or (lambda v: auto(key, v)))(row.get(key)))


def table(rows: Sequence[Row], columns: Sequence[Column]) -> str:
    """A markdown table (or ``_no rows_``)."""
    if not rows:
        return "_no rows_"
    head = "| " + " | ".join(label for label, _ in columns) + " |"
    rule = "|" + "---|" * len(columns)
    body = ["| " + " | ".join(get(r) for _, get in columns) + " |" for r in rows]
    return "\n".join([head, rule, *body])


def auto_table(rows: Sequence[Row], limit: int = 0) -> str:
    """A table of every scalar column of ``rows`` (shape-agnostic)."""
    rows = list(rows)[: limit or None]
    keys = [k for k, v in (rows[0].items() if rows else ()) if not _nested(v)]
    return table(rows, [col(k) for k in keys])


def counts(payload: Row, name: str, shown: int) -> str:
    """``N of M rows`` from the API's ``_tables`` metadata when present."""
    meta = payload.get("_tables", {}).get(name)
    if not meta:
        return f"{shown} rows"
    return f"{meta.get('returned', shown)} of {meta.get('matched', '?')} rows"


def _nested(value: object) -> bool:
    """Lists and objects do not fit a cell."""
    return isinstance(value, list | dict)


def local_table(rows: Sequence[Row], search: str, sort: str, limit: int) -> list[Row]:
    """Search/sort/limit client-side, for an API without the table grammar.

    Same semantics as the API: case-insensitive substring over scalar cells;
    ``-col`` sorts descending; nulls last either way.
    """
    needle = search.lower()
    out = [
        r
        for r in rows
        if not needle
        or any(needle in str(v).lower() for v in r.values() if not _nested(v))
    ]
    for key in reversed([k.strip() for k in sort.split(",") if k.strip()]):
        name, desc = key.lstrip("-"), key.startswith("-")
        present = [r for r in out if r.get(name) is not None]
        present.sort(key=lambda r, n=name: r[n], reverse=desc)
        out = present + [r for r in out if r.get(name) is None]
    return out[: limit or None]
