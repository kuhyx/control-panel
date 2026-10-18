"""Payload -> compact markdown, one renderer per tool.

Renderers are pure: they take the API's JSON and return text, so every one
is tested without a server.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import quote

from control_panel_mcp import _fmt
from control_panel_mcp._fmt import col, table, usd

Row = dict[str, Any]
UI = "http://127.0.0.1:8760/#/tokens"
NOTE = "_$ = API list-price estimate, not the subscription bill._"
DAYS_SHOWN = 14
TOP = 10


def session_link(key: str) -> str:
    """The UI's drill-down for one session (subagent keys contain ``/``)."""
    return f"{UI}/s/{quote(key, safe='')}"


def _period(payload: Row) -> str:
    """The filter window the API applied."""
    found = payload.get("filters", {})
    span = f"{_fmt.day(found.get('since'))}..{_fmt.day(found.get('until'))}"
    extra = [f"{k}={found[k]}" for k in ("cwd", "model") if found.get(k)]
    if found.get("scope", "all") != "all":
        extra.append(f"scope={found['scope']}")
    return " ".join([span, *extra])


def overview(payload: Row) -> str:
    """Tiles, the last two weeks by day, and weeks."""
    tiles = payload.get("tiles", {})
    head = (
        f"**Spend {_period(payload)}**: {usd(tiles.get('usd'))} total,"
        f" {usd(tiles.get('usd_per_day'))}/day, {_fmt.num(tiles.get('calls'))}"
        f" calls ({usd(tiles.get('usd_per_call'))}/call),"
        f" {_fmt.num(tiles.get('sessions'))} sessions,"
        f" {_fmt.num(tiles.get('active_h'))} active h"
    )
    daily = payload.get("daily", [])[-DAYS_SHOWN:]
    days = table(
        daily,
        [
            col("day"),
            col("usd", "$"),
            col("calls"),
            col("usd_per_call", "$/call"),
            col("sub_share", "sub"),
            col("opus_share", "opus"),
            col("over_share", "over-budget"),
            col("home_share", "~ cwd"),
        ],
    )
    weeks = table(
        payload.get("weekly", []), [col("week"), col("usd", "$"), col("calls")]
    )
    return f"{head}\n\n{days}\n\n{weeks}\n\n{NOTE} UI: {UI}"


def sessions(payload: Row) -> str:
    """The ranked session list."""
    rows = payload.get("sessions", [])
    body = table(
        rows,
        [
            col("key"),
            col("usd", "$"),
            col("usd_sub", "sub $"),
            col("calls"),
            col("prompts"),
            col("subagents", "subs"),
            col("active_s", "active"),
            col("final_tag", "tag", _fmt.cell),
            col("cwd", fmt=lambda v: _fmt.cell(v, 30)),
            col("title", fmt=lambda v: _fmt.cell(v, 40)),
        ],
    )
    return (
        f"**Sessions {_period(payload)}**"
        f" ({_fmt.counts(payload, 'sessions', len(rows))})"
        f"\n\n{body}\n\n{NOTE} Drill down: session_detail(key)."
    )


def session_detail(payload: Row) -> str:
    """One session: per prompt, top subagents, top tools."""
    found = payload.get("session", {})
    prompts = payload.get("prompts", [])
    head = (
        f"**{_fmt.cell(found.get('title'))}** `{found.get('key')}`\n"
        f"{usd(found.get('usd'))} (main {usd(found.get('usd_main'))}, subagents"
        f" {usd(found.get('usd_sub'))}), {_fmt.num(found.get('calls'))} calls,"
        f" active {_fmt.dur(found.get('active_s'))}, cwd"
        f" {_fmt.cell(found.get('cwd'))}, tag {found.get('final_tag') or '-'}"
    )
    per_prompt = table(
        prompts,
        [
            col("idx", "#"),
            col("usd", "$"),
            col("usd_sub", "sub $"),
            col("calls"),
            col("active_s", "active"),
            col("text", "prompt", lambda v: _fmt.cell(v, 50)),
        ],
    )
    subs = sorted(
        (s for p in prompts for s in p.get("subagents", [])),
        key=lambda s: -(s.get("usd") or 0),
    )[:TOP]
    agents = table(
        subs,
        [
            col("usd", "$"),
            col("agent_type", "type", _fmt.cell),
            col("model", fmt=_fmt.cell),
            col("calls"),
            col("description", fmt=lambda v: _fmt.cell(v, 50)),
        ],
    )
    tools = table(_tool_totals(prompts), [col("name", "tool", _fmt.cell), *_MONEY])
    return (
        f"{head}\n\n{per_prompt}\n\n**Top subagents**\n{agents}\n\n**Tools**\n"
        f"{tools}\n\n{NOTE} UI: {session_link(str(found.get('key', '')))}"
    )


_MONEY = [col("calls"), col("usd", "$"), col("carry_usd", "carry $")]


def _tool_totals(prompts: list[Row]) -> list[Row]:
    """Tool rows summed over prompts, most expensive first."""
    totals: dict[str, Row] = defaultdict(
        lambda: {"calls": 0, "usd": 0.0, "carry_usd": 0.0}
    )
    for tool in (t for p in prompts for t in p.get("tools", [])):
        entry = totals[tool.get("name", "?")]
        for key in ("calls", "usd", "carry_usd"):
            entry[key] += tool.get(key) or 0
    rows = [{"name": name, **v} for name, v in totals.items()]
    return sorted(rows, key=lambda r: -r["usd"])[:TOP]


def grouped(payload: Row, group: str, limit: int, title: str) -> str:
    """One table out of a panel, whatever its columns."""
    rows = payload.get(group)
    if not isinstance(rows, list):
        keys = [k for k, v in payload.items() if isinstance(v, list)]
        return f"no `{group}` table in {title}; tables: {', '.join(keys) or 'none'}"
    return (
        f"**{title}: {group} {_period(payload)}**"
        f" ({_fmt.counts(payload, group, min(len(rows), limit or len(rows)))})\n\n"
        f"{_fmt.auto_table(rows, limit)}\n\n{NOTE}"
    )


def all_tables(payload: Row, title: str, limit: int = TOP) -> str:
    """Every table of a panel, capped at ``limit`` rows each."""
    parts = [f"**{title} {_period(payload)}**"]
    parts += [
        f"{v}" for k, v in payload.items() if isinstance(v, str) and k != "_tables"
    ]
    for key, rows in payload.items():
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            parts.append(f"**{key}**\n{_fmt.auto_table(rows, limit)}")
    return "\n\n".join([*parts, NOTE])
