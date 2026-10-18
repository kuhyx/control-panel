"""Search, filter, sort and limit any table in any /api/tokens response.

A *table* is a list of dicts anywhere in a response; its id is its key path
with list levels collapsed (``sessions``, ``prompts.tools``). The UI and any
other client send the same query parameters, so both get identical rows:

    t.<id>.q=<text>              rows whose scalar cells contain <text>
    t.<id>.f.<column>=~<text>    the column contains <text>
    t.<id>.f.<column>=<lo>..<hi> numeric range, either end optional
    t.<id>.f.<column>==<a>|<b>   the column is one of the values
    t.<id>.sort=-usd,calls       sort keys in order; "-" means descending
    t.<id>.limit=<n>             at most n rows (0: all)

Matching is case-insensitive; nulls sort last either way. Every response
gains ``_tables``: per table, how many rows there were, matched and were
returned, and each column's kind (number / enum / text) with enum values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any
from urllib.parse import parse_qs

ENUM_MIN = 2  # one repeated value offers no choice
ENUM_MAX = 30
ENUM_CHARS = 40  # longer values make a useless pick list: filter as text
PREFIX = "t."
Row = dict[str, Any]


@dataclass
class Spec:
    """One table's parameters."""

    search: str = ""
    filters: dict[str, str] = field(default_factory=dict)
    sort: list[tuple[str, bool]] = field(default_factory=list)
    limit: int | None = None


def parse(
    query: str, defaults: dict[str, dict[str, str]] | None = None
) -> dict[str, Spec]:
    """Table specs by id, from a query string (plus per-table defaults)."""
    raw: dict[str, dict[str, str]] = {k: dict(v) for k, v in (defaults or {}).items()}
    for key, values in parse_qs(query, keep_blank_values=True).items():
        if not key.startswith(PREFIX):
            continue
        for op in (".q", ".sort", ".limit"):
            if key.endswith(op):
                raw.setdefault(key[len(PREFIX) : -len(op)], {})[op[1:]] = values[-1]
                break
        else:
            table, sep, column = key[len(PREFIX) :].partition(".f.")
            if sep:
                raw.setdefault(table, {})["f." + column] = values[-1]
    return {table: _spec(params) for table, params in raw.items()}


def _spec(params: dict[str, str]) -> Spec:
    """Decode one table's raw parameters."""
    sort = [
        (key.lstrip("-"), key.startswith("-"))
        for key in params.get("sort", "").split(",")
        if key.strip("-")
    ]
    limit = params.get("limit", "")
    return Spec(
        search=params.get("q", "").lower(),
        filters={k[2:]: v for k, v in params.items() if k.startswith("f.") and v},
        sort=sort,
        limit=int(limit) if limit.isdigit() else None,
    )


def _text(value: object) -> str:
    """A cell as lower-case text (null: empty)."""
    if value is None:
        return ""
    return value.lower() if isinstance(value, str) else json.dumps(value).lower()


def _number(text: str) -> float | None:
    """A range bound, ``None`` when blank or not a number."""
    try:
        return float(text)
    except ValueError:
        return None


def _matches(value: object, rule: str) -> bool:
    """Whether one cell passes one column filter."""
    if rule.startswith("~"):
        return rule[1:].lower() in _text(value)
    if rule.startswith("="):
        return _text(value) in {v.lower() for v in rule[1:].split("|")}
    low, _, high = rule.partition("..")
    if not isinstance(value, int | float) or isinstance(value, bool):
        return False
    lo, hi = _number(low), _number(high)
    return (lo is None or value >= lo) and (hi is None or value <= hi)


def _keep(row: Row, spec: Spec) -> bool:
    """Whether a row passes the search and every column filter."""
    if spec.search and not any(
        spec.search in _text(v) for v in row.values() if not isinstance(v, list | dict)
    ):
        return False
    return all(_matches(row.get(col), rule) for col, rule in spec.filters.items())


def _sorted(rows: list[Row], keys: list[tuple[str, bool]]) -> list[Row]:
    """Stable multi-key sort, nulls last in both directions."""
    for column, descending in reversed(keys):
        present = [r for r in rows if r.get(column) is not None]
        missing = [r for r in rows if r.get(column) is None]
        present.sort(key=lambda r, c=column: _sort_key(r[c]), reverse=descending)
        rows = present + missing
    return rows


def _sort_key(value: object) -> tuple[int, Any]:
    """Numbers before text; text compared case-insensitively."""
    if isinstance(value, int | float):
        return (0, value)
    return (1, _text(value))


def _kind(values: list[object]) -> dict[str, Any]:
    """A column's kind, with the distinct values of an enum."""
    present = [v for v in values if v is not None]
    if present and all(
        isinstance(v, int | float) and not isinstance(v, bool) for v in present
    ):
        return {"kind": "number"}
    if any(isinstance(v, list | dict) for v in present):
        return {"kind": "object"}
    distinct = sorted({_text(v) if not isinstance(v, str) else v for v in present})
    short = all(len(v) <= ENUM_CHARS for v in distinct)
    if short and ENUM_MIN <= len(distinct) <= ENUM_MAX and len(distinct) < len(present):
        return {"kind": "enum", "values": distinct}
    return {"kind": "text"}


def _columns(rows: list[Row]) -> dict[str, Any]:
    """Every column's kind, over all rows (before filtering)."""
    names: dict[str, None] = {}
    for row in rows:
        names.update(dict.fromkeys(row))
    return {name: _kind([r.get(name) for r in rows]) for name in names}


def _note(
    meta: dict[str, Any], table: str, rows: list[Row], kept: int, shown: int
) -> None:
    """Accumulate one list's counts (a nested table spans many lists)."""
    entry = meta.setdefault(
        table, {"total": 0, "matched": 0, "shown": 0, "columns": {}}
    )
    entry["total"] += len(rows)
    entry["matched"] += kept
    entry["shown"] += shown
    entry["columns"].update(_columns(rows))


def _table(rows: list[Row], spec: Spec) -> tuple[list[Row], int]:
    """Filtered, sorted, limited rows and how many matched."""
    kept = [r for r in rows if _keep(r, spec)]
    ordered = _sorted(kept, spec.sort)
    if spec.limit:
        ordered = ordered[: spec.limit]
    return ordered, len(kept)


def _walk(node: Row, specs: dict[str, Spec], prefix: str, meta: dict[str, Any]) -> Row:
    """Apply the specs to every table under ``node``."""
    out: Row = {}
    for key, value in node.items():
        if isinstance(value, list) and all(isinstance(v, dict) for v in value):
            table = prefix + key
            rows, kept = _table(value, specs.get(table, Spec()))
            _note(meta, table, value, kept, len(rows))
            out[key] = [_walk(r, specs, table + ".", meta) for r in rows]
        elif isinstance(value, dict) and key != "_tables":
            out[key] = _walk(value, specs, f"{prefix}{key}.", meta)
        else:
            out[key] = value
    return out


def apply(
    payload: Row, query: str, defaults: dict[str, dict[str, str]] | None = None
) -> Row:
    """``payload`` with every table searched/filtered/sorted/limited."""
    meta: dict[str, Any] = {}
    out = _walk(payload, parse(query, defaults), "", meta)
    out["_tables"] = meta
    return out
