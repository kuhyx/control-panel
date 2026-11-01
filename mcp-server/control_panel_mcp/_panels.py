"""Renderers for the context, levers, A/B and efficiency panels.

The optimisation prompt lives in :mod:`_prompt` (a port of the UI's).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from control_panel_mcp import _fmt, _prompt
from control_panel_mcp._fmt import col, table, usd
from control_panel_mcp._views import NOTE, UI

Row = dict[str, Any]
_METRICS = ("redo", "followup", "error", "correction")


def file_link(path: str) -> str:
    """The UI's drill-down for one context file."""
    return f"{UI}/f/{quote(path, safe='')}"


def context_files(payload: Row, *, over_limit_only: bool) -> str:
    """Context files by $/day, optionally only those over a limit or budget."""
    files = payload.get("files", [])
    if over_limit_only:
        files = _prompt.over_limit(files)
    body = table(
        files,
        [
            col("path", fmt=lambda v: _fmt.cell(v, 55)),
            col("standing", fmt=_fmt.cell),
            col("lines"),
            col("tokens"),
            col("usd_per_day", "$/day"),
            ("status", _prompt.status),
            col("warning", fmt=lambda v: _fmt.cell(v, 50)),
        ],
    )
    return (
        f"**Context files** ({len(files)}; {_fmt.num(payload.get('calls_per_day'))}"
        f" calls/day at ${payload.get('price_per_mtok', 0)}/MTok cache read)\n\n"
        f"{body}\n\n{NOTE} Fix: optimization_prompt(paths). UI: {UI}"
    )


def levers(payload: Row, status: str) -> str:
    """The lever ledger, optionally one status."""
    rows = payload.get("rows", [])
    if status:
        rows = [r for r in rows if str(r.get("status", "")).lower() == status.lower()]
    body = table(
        rows,
        [
            col("date"),
            col("status", fmt=_fmt.cell),
            col("outcome", fmt=_fmt.cell),
            col("lever", fmt=lambda v: _fmt.cell(v, 70)),
            col("metric", fmt=_fmt.cell),
            col("baseline", "base"),
            col("predicted", "pred"),
            col("actual"),
        ],
    )
    return f"**Levers** ({len(rows)} rows)\n\n{body}\n\nUI: {UI}"


def _rate(cell: object) -> str:
    """``12% [5-20%] k/n`` from a {k, rate, low, high} cell."""
    if not isinstance(cell, dict):
        return "-"
    return (
        f"{_fmt.share(cell.get('rate'))} [{_fmt.share(cell.get('low'))}-"
        f"{_fmt.share(cell.get('high'))}] k={cell.get('k')}"
    )


def _ab_section(title: str, payload: Row, suffix: str = "") -> str:
    """One experiment: its banner and one row per arm."""
    arms = [{"arm": name, **arm} for name, arm in payload.get("arms", {}).items()]
    body = table(
        arms,
        [
            col("arm"),
            col("n"),
            *[col(m, fmt=_rate) for m in _METRICS],
            col("usd", "$ mean", lambda v: usd((v or {}).get("mean"))),
            col("duration_s", "dur mean", lambda v: _fmt.dur((v or {}).get("mean"))),
        ],
    )
    banner = payload.get("banner") or {}
    return (
        f"**{title}**{suffix}: {banner.get('level', '-')}: {banner.get('text', '')}\n\n"
        f"{body}\n\nunjoined: {payload.get('unjoined', 0)}."
    )


def ab_status(payload: Row) -> str:
    """The judgment A/B and, when present, the build A/B, each with its arms."""
    build = payload.get("build")
    if not isinstance(build, dict):
        section = _ab_section("A/B judgment subagents", payload)
        return f"{section} Rates are 95% CIs. {NOTE}"
    parts = [
        _ab_section("A/B judgment subagents", payload, " (closed experiment)"),
        _ab_section("A/B build subagents", build),
    ]
    return "\n\n".join([*parts, f"Rates are 95% CIs. {NOTE}"])


def efficiency(payload: Row) -> str:
    """$ per DONE session, per surviving commit, per size unit, by week."""
    parts = [f"**Efficiency** ({payload.get('filtered_by', 'filters applied')})"]
    for name in ("done", "commits", "estimate"):
        caption = payload.get("captions", {}).get(name, "")
        rows = payload.get(name, [])[-8:]
        parts.append(f"**{name}**: {caption}\n{_fmt.auto_table(rows)}")
    return "\n\n".join([*parts, NOTE])
