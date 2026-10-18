"""Standing prefix: what every API call re-reads before it does anything.

Two views of the same bill. The token_audit snapshots carry one global
``standing_tokens_est`` (every surface: CLAUDE.md, memories, rules, skill and
agent descriptions, MCP tool names...); the store keeps no per-surface split
of it. The per-surface view instead replays ``context_sizes`` (git history and
prune runs, whole-file bytes) for the files ``context_files`` marks as always
loaded, grouped by their kind. Either is priced as
``tokens x API calls/day x cache-read price``.
"""

from __future__ import annotations

from collections import defaultdict
import json
from typing import TYPE_CHECKING, Any

from control_panel.tokens import _db
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    from collections.abc import Iterable
    import sqlite3

    from control_panel.tokens._db import Filters

BYTES_PER_TOKEN = 4  # token_audit.surfaces.BYTES_PER_TOKEN
WINDOW_DAYS = 7  # the calls/day window, as the context-files panel uses
TOP = 25
FILTERED_BY = (
    "date range only for sizes, prunes and snapshots (they are global);"
    " calls/day honours date, cwd, model and scope"
)
CAPTION = (
    "Standing prefix = context loaded on every API call. Per-surface tokens"
    " replay the stored size history (git + prune runs) of the always-loaded"
    " files, bytes/4; the audit estimate is token_audit's standing_tokens_est"
    " (all surfaces, from disk). $/day = tokens x API calls/day (the 7 days"
    " before the range end, under cwd/model/scope) x the cache-read price; it"
    " assumes every call, subagents included, carries the whole prefix."
    " Skill/agent descriptions and repo CLAUDE.md files are not in the"
    " per-surface view: their history is whole-file bytes, or only loads in"
    " one repo. Sizes and snapshots are global: cwd/model/scope do not narrow"
    " them."
)

_CALLS = (
    "SELECT COUNT(*) FROM turns WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
)
_SIZES = (
    "SELECT s.path, s.ts, s.bytes, f.kind FROM context_sizes s"
    " JOIN context_files f ON f.path = s.path"
    " WHERE f.standing = 'always' AND s.ts <= ? ORDER BY s.ts"
)
_PRUNES = (
    "SELECT h.path, h.ts, h.bytes, h.source, h.prev, f.kind FROM ("
    " SELECT path, ts, bytes, source,"
    " LAG(bytes) OVER (PARTITION BY path ORDER BY ts) AS prev"
    " FROM context_sizes) h"
    " LEFT JOIN context_files f ON f.path = h.path"
    " WHERE (h.source = 'git' OR h.source LIKE 'prune%')"
    " AND h.ts BETWEEN ? AND ? ORDER BY h.ts DESC"
)
_SNAPSHOTS = (
    "SELECT name, metrics FROM snapshots WHERE until BETWEEN ? AND ? ORDER BY until"
)


def _calls_per_day(conn: sqlite3.Connection, filters: Filters) -> float:
    """API calls per day over the week before the range end, under the filters."""
    params = (filters.until - WINDOW_DAYS * 86400, *filters.params()[1:])
    return float(conn.execute(_CALLS, params).fetchone()[0]) / WINDOW_DAYS


def _by_kind(state: dict[str, tuple[str, int]]) -> dict[str, list[int]]:
    """Per surface kind: [tokens, files with any bytes]."""
    kinds: defaultdict[str, list[int]] = defaultdict(lambda: [0, 0])
    for kind, size in state.values():
        kinds[kind][0] += size
        kinds[kind][1] += size > 0
    return {k: [size // BYTES_PER_TOKEN, files] for k, (size, files) in kinds.items()}


def _total(state: dict[str, tuple[str, int]]) -> int:
    """All always-loaded files' tokens (the surface rows' sum)."""
    return sum(tokens for tokens, _ in _by_kind(state).values())


def _replay(
    rows: Iterable[tuple[str, float, int, str]], filters: Filters
) -> tuple[dict[str, list[int]], dict[str, list[int]], list[dict[str, Any]]]:
    """Surface sizes at the range start and end, and the daily step series."""
    state: dict[str, tuple[str, int]] = {}
    start: dict[str, list[int]] | None = None
    days: dict[str, int] = {}
    for path, ts, size, kind in rows:
        if ts >= filters.since and start is None:
            start = _by_kind(state)
            if state:
                days[_db.day_of(filters.since)] = _total(state)
        state[path] = (kind, size or 0)
        if ts >= filters.since:
            days[_db.day_of(ts)] = _total(state)
    if start is None:
        start = _by_kind(state)
        if state:
            days[_db.day_of(filters.since)] = _total(state)
    if state:
        days[_db.day_of(filters.until)] = _total(state)
    points = [{"day": d, "tokens": t} for d, t in sorted(days.items())]
    return start, _by_kind(state), points


def _usd(tokens: int | None, calls: float, price: float) -> float | None:
    """What carrying ``tokens`` on every call costs per day."""
    return None if tokens is None else tokens * calls * price / 1e6


def _surfaces(
    start: dict[str, list[int]], end: dict[str, list[int]], calls: float, price: float
) -> list[dict[str, Any]]:
    """One row per surface kind, costliest first."""
    rows = []
    for kind in start.keys() | end.keys():
        tokens, files = end.get(kind, [0, 0])
        first = start.get(kind, [0, 0])[0]
        rows.append(
            {
                "surface": kind,
                "files": files,
                "start_tokens": first,
                "tokens": tokens,
                "delta_tokens": tokens - first,
                "usd_per_day": _usd(tokens, calls, price),
            }
        )
    return sorted(rows, key=lambda r: (-r["tokens"], r["surface"]))


def _prunes(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """Every size point in range, newest first, with its change."""
    return [
        {
            "ts": ts,
            "path": path,
            "surface": kind or "not standing",
            "source": source,
            "bytes": size,
            "delta_bytes": None if prev is None else size - prev,
        }
        for path, ts, size, source, prev, kind in conn.execute(
            _PRUNES, (filters.since, filters.until)
        )
    ]


def _audit(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """token_audit's whole-prefix estimate per snapshot in range."""
    points = []
    for name, metrics in conn.execute(_SNAPSHOTS, (filters.since, filters.until)):
        standing = json.loads(metrics or "{}").get("standing_tokens_est")
        if standing is not None:
            points.append({"day": name, "tokens": standing})
    return points


@panel(
    "prefix",
    "Standing prefix",
    order=64,
    tables={"surfaces": {"limit": str(TOP)}, "prunes": {"limit": str(TOP)}},
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Standing-prefix size per surface over time, its $/day, prune history."""
    price = float(_db.meta(conn, "cache_read_usd_per_mtok") or 0.0)
    calls = _calls_per_day(conn, filters)
    start, end, points = _replay(conn.execute(_SIZES, (filters.until,)), filters)
    audit = _audit(conn, filters)
    prunes = _prunes(conn, filters)
    audit_tokens = audit[-1]["tokens"] if audit else None
    files_tokens = sum(tokens for tokens, _ in end.values())
    return {
        "caption": CAPTION,
        "filtered_by": FILTERED_BY,
        "totals": {
            "audit_tokens": audit_tokens,
            "files_tokens": files_tokens,
            "calls_per_day": calls,
            "price_per_mtok": price,
            "audit_usd_per_day": _usd(audit_tokens, calls, price),
            "files_usd_per_day": _usd(files_tokens, calls, price),
            "pruned_bytes": sum(
                -r["delta_bytes"]
                for r in prunes
                if r["source"].startswith("prune") and (r["delta_bytes"] or 0) < 0
            ),
        },
        "series": [
            {"label": "always-loaded files", "points": points},
            {"label": "audit estimate (all surfaces)", "points": audit},
        ],
        "surfaces": _surfaces(start, end, calls, price),
        "prunes": prunes,
    }
