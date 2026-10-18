"""Read-only MCP server over kuhy's token-cost dashboard (``/api/tokens``).

Run from the dedicated venv (``mcp-server/scripts/setup_mcp.sh`` registers it at
user scope)::

    ~/.venvs/control-panel-mcp/bin/python -m control_panel_mcp._mcp

Invariants: READ-ONLY (GETs only, never the SQLite store); stdout is the
JSON-RPC channel, so logging goes to stderr; tool descriptions stay terse
because every schema sits in every session's prompt prefix.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

from mcp.server.mcpserver import MCPServer

from control_panel_mcp import _client, _fmt, _panels, _prompt, _views

if TYPE_CHECKING:
    from collections.abc import Callable

logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stderr,
    format="%(asctime)s [%(levelname)s] token-dashboard-mcp: %(message)s",
)

mcp = MCPServer("token-dashboard")
Row = dict[str, Any]
W = " window: 7d|YYYY-MM-DD..YYYY-MM-DD|snapshot; ''=30d."
J = " as_json=raw."


def _tool(description: str) -> Callable[[Callable[..., str]], Callable[..., str]]:
    """Register a text-only tool: no output schema, no structuredContent copy.

    Structured output would add an output schema to every tool listing and
    repeat each answer inside ``structuredContent``: tokens for nothing.
    """
    return mcp.tool(description=description, structured_output=False)


def _answer(
    fetch: Callable[[], Row],
    render: Callable[[Row], str],
    *,
    as_json: bool = False,
    missing: str = "",
) -> str:
    """Fetch, then render (or dump) under the cap; errors become text."""
    try:
        payload = fetch()
    except _client.DashboardError as exc:
        return missing if missing and _client.is_missing(exc) else str(exc)
    return _fmt.as_json(payload) if as_json else _fmt.cap(render(payload))


def _panel(name: str, params: dict[str, str] | None = None) -> Callable[[], Row]:
    """A deferred GET of one panel."""
    return lambda: _client.get(f"/panel/{name}", params)


@_tool("Spend tiles, $/day, last 14 days, weeks." + W + J)
def overview(window: str = "", *, as_json: bool = False) -> str:
    """Spend overview."""
    return _answer(
        _panel("overview", _client.window_params(window)),
        _views.overview,
        as_json=as_json,
    )


@_tool(
    "Rank sessions. search: text; filters: 'cwd=..&model=..&scope=sub"
    "&window=7d&<column>=~text|lo..hi|=a|b'; sort: '-usd,calls'; limit: 0=all." + J
)
def sessions(
    search: str = "",
    filters: str = "",
    sort: str = "-usd",
    limit: int = 20,
    *,
    as_json: bool = False,
) -> str:
    """Ranked session list."""
    params = {
        **_client.filter_params(filters, "sessions"),
        **_client.table_params("sessions", search, sort, limit),
    }

    def fetch() -> Row:
        payload = _client.get("/panel/sessions", params)
        if "_tables" not in payload:  # API without the table grammar yet
            payload["sessions"] = _fmt.local_table(
                payload.get("sessions", []), search, sort, limit
            )
        return payload

    return _answer(fetch, _views.sessions, as_json=as_json)


@_tool("One session: $ per prompt, top subagents, tools, UI link." + J)
def session_detail(session_id: str, *, as_json: bool = False) -> str:
    """One session's drill-down."""
    return _answer(
        lambda: _client.get(f"/session/{session_id}"),
        _views.session_detail,
        as_json=as_json,
    )


@_tool(
    "Carry cost (context kept alive) by group_by: families|mcp|skills|"
    "context_reads|web|images|rereads|hooks|attachments|daily. Needs the carry "
    "panel (in progress)." + W + J
)
def carry_costs(
    group_by: str = "families",
    window: str = "",
    limit: int = 15,
    *,
    as_json: bool = False,
) -> str:
    """Carry-cost attribution."""
    params = {
        **_client.window_params(window),
        **_client.table_params(group_by, "", "", limit),
    }
    return _answer(
        _panel("carry", params),
        lambda p: _views.grouped(p, group_by, limit, "Carry cost"),
        as_json=as_json,
        missing="carry panel not built yet (TODO group D)",
    )


@_tool("Context files: tokens, $/day, limit breaches." + J)
def context_files(*, over_limit_only: bool = False, as_json: bool = False) -> str:
    """Context-file inspector."""
    return _answer(
        _panel("context"),
        lambda p: _panels.context_files(p, over_limit_only=over_limit_only),
        as_json=as_json,
    )


@_tool(
    "The UI's 'Copy optimisation prompt' text. paths: path suffixes;"
    " default: every file over a limit."
)
def optimization_prompt(paths: list[str] | None = None) -> str:
    """Context-file optimisation prompt."""
    return _answer(_panel("context"), lambda p: _prompt.for_payload(p, paths or []))


@_tool("Lever ledger. status: applied|proposed|'not applied'|''." + J)
def levers(status: str = "", *, as_json: bool = False) -> str:
    """Levers and their measured outcomes."""
    return _answer(
        _panel("levers"), lambda p: _panels.levers(p, status), as_json=as_json
    )


@_tool("$ per DONE session, per kept commit, per size unit." + W + J)
def efficiency(window: str = "", *, as_json: bool = False) -> str:
    """Weekly efficiency ratios."""
    return _answer(
        _panel("efficiency", _client.window_params(window)),
        _panels.efficiency,
        as_json=as_json,
    )


@_tool("A/B of judgment subagents (sonnet vs opus): banner, CIs." + J)
def ab_status(*, as_json: bool = False) -> str:
    """The A/B experiment."""
    return _answer(_panel("ab"), _panels.ab_status, as_json=as_json)


@_tool("Hook cost: injected context + carry (planned panel)." + W + J)
def hooks(window: str = "", *, as_json: bool = False) -> str:
    """Hooks: their own panel when built, else the carry panel's hooks table."""
    params = _client.window_params(window)

    def fetch() -> Row:
        try:
            return _client.get("/panel/hooks", params)
        except _client.DashboardError as exc:
            if not _client.is_missing(exc):
                raise
            return _client.get("/panel/carry", params)

    return _answer(
        fetch,
        lambda p: (
            _views.all_tables(p, "Hooks")
            if "hooks" not in p
            else _views.grouped(p, "hooks", 0, "Hooks")
        ),
        as_json=as_json,
        missing="hooks panel not built yet (TODO groups D/F)",
    )


@_tool("Spikes, runaway sessions/loops (planned panel)." + W + J)
def anomalies(window: str = "", *, as_json: bool = False) -> str:
    """Anomalies panel."""
    return _answer(
        _panel("anomalies", _client.window_params(window)),
        lambda p: _views.all_tables(p, "Anomalies"),
        as_json=as_json,
        missing="anomalies panel not built yet (TODO group N)",
    )


def main() -> None:
    """Serve over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
